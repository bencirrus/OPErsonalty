"""Live data adapters for the SF OPE Homebase portal.

Sources (all keyless, no API token needed):
- DataSF Socrata: DBI Building Permits (i98e-djp9)
- DataSF Socrata: Rent Board Housing Inventory (gdc7-dmcn)
- FRED MORTGAGE30US via fredgraph.csv (Freddie Mac PMMS weekly 30-yr rate)

Every public function returns None on any failure (network down, throttled,
schema change) so the app always falls back to the seeded demo data. Results
are cached on disk for CACHE_TTL seconds so a demo run does not hammer the
keyless throttled tier.

Note: DataSF's edge blocks SoQL queries that combine $select with $where
(403 from its WAF), so queries fetch full rows and project fields locally.
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

DBI_DATASET = 'i98e-djp9'          # DBI Building Permits
RENTBOARD_DATASET = 'gdc7-dmcn'    # Rent Board Housing Inventory
DBI_URL = 'https://data.sfgov.org/Housing-and-Buildings/Building-Permits/i98e-djp9'
RENTBOARD_URL = 'https://data.sfgov.org/Housing-and-Buildings/Rent-Board-Housing-Inventory/gdc7-dmcn'
FRED_URL = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US'
FRED_SERIES_URL = 'https://fred.stlouisfed.org/series/mortgage30us'

CACHE_PATH = Path(__file__).parent / '.livedata-cache.json'
CACHE_TTL_SECONDS = 6 * 3600
TIMEOUT_SECONDS = 8
_UA = {'User-Agent': 'sf-ope-homebase-demo/1.0 (+https://github.com/bencirrus/OPErsonalty)',
       'Accept': 'application/json'}


def _http_get(url):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        return resp.read()


def _socrata(dataset, **params):
    url = 'https://data.sfgov.org/resource/%s.json?%s' % (dataset, urllib.parse.urlencode(params))
    return json.loads(_http_get(url))


def _cache_read():
    try:
        return json.loads(CACHE_PATH.read_text())
    except Exception:
        return {}


def _cache_write(cache):
    try:
        CACHE_PATH.write_text(json.dumps(cache))
    except Exception:
        pass


def _cached(key, fetch):
    cache = _cache_read()
    hit = cache.get(key)
    now = time.time()
    if hit and now - hit.get('ts', 0) < CACHE_TTL_SECONDS:
        return hit['value']
    value = fetch()
    if value is not None:
        cache[key] = {'ts': now, 'value': value}
        _cache_write(cache)
    return value


_SUFFIX_MAP = {'ave': 'Av', 'avenue': 'Av', 'st': 'St', 'street': 'St', 'blvd': 'Bl',
               'boulevard': 'Bl', 'rd': 'Rd', 'road': 'Rd', 'dr': 'Dr', 'drive': 'Dr',
               'ln': 'Ln', 'lane': 'Ln', 'ct': 'Ct', 'court': 'Ct', 'pl': 'Pl', 'ter': 'Ter'}


def _norm_street_name(name):
    """DBI zero-pads single-digit ordinal streets: '6th' -> '06th'."""
    for sep in (' ', ''):
        pass
    if name and name[0].isdigit():
        digits = ''
        rest = name
        while rest and rest[0].isdigit():
            digits += rest[0]
            rest = rest[1:]
        return digits.zfill(2) + rest
    return name


def _norm_suffix(suffix):
    return _SUFFIX_MAP.get((suffix or '').lower(), suffix)


def dbi_permits(street_number, street_name, street_suffix):
    """Live DBI building permits for one address, newest first. None on failure."""
    street_name = _norm_street_name(street_name)
    street_suffix = _norm_suffix(street_suffix)
    def fetch():
        where = ('street_number="%s" AND upper(street_name)=upper("%s") '
                 'AND upper(street_suffix)=upper("%s")' % (street_number, street_name, street_suffix))
        rows = _socrata(DBI_DATASET, **{
            '$where': where, '$order': 'permit_creation_date DESC', '$limit': '30'})
        if not isinstance(rows, list):
            return None
        return [{
            'permit_number': r.get('permit_number'),
            'status': r.get('status'),
            'filed': (r.get('permit_creation_date') or '')[:10],
            'existing_units': r.get('existing_units'),
            'proposed_units': r.get('proposed_units'),
            'description': (r.get('description') or '').strip(),
        } for r in rows]
    return _cached('dbi:%s %s %s' % (street_number, street_name, street_suffix), fetch)


def rent_board_block(block_address):
    """Live Rent Board Housing Inventory submissions for one block. None on failure."""
    def fetch():
        rows = _socrata(RENTBOARD_DATASET, **{
            '$where': 'block_address="%s"' % block_address,
            '$order': 'signature_date DESC', '$limit': '100'})
        if not isinstance(rows, list):
            return None
        return [{
            'block_address': r.get('block_address'),
            'unit_count': r.get('unit_count'),
            'case_type': r.get('case_type_name'),
            'occupancy': r.get('occupancy_type'),
            'signed': (r.get('signature_date') or '')[:10],
        } for r in rows]
    return _cached('rentboard:%s' % block_address, fetch)


def _as_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def summarize_dbi(permits):
    """Compress raw DBI rows into the facts the Permit & Zoning Analyst needs."""
    if not permits:
        return None
    latest = permits[0]
    existing = [_as_float(p['existing_units']) for p in permits]
    existing = [u for u in existing if u is not None]
    proposed = [_as_float(p['proposed_units']) for p in permits]
    proposed = [u for u in proposed if u is not None]
    additions = [p for p in permits
                 if _as_float(p['proposed_units']) is not None
                 and _as_float(p['existing_units']) is not None
                 and _as_float(p['proposed_units']) > _as_float(p['existing_units'])]
    return {
        'permit_count': len(permits),
        'latest_permit': latest['permit_number'],
        'latest_status': latest['status'],
        'latest_filed': latest['filed'],
        'latest_units_existing': _as_float(latest['existing_units']),
        'max_units_on_record': max(existing) if existing else None,
        'max_units_proposed': max(proposed) if proposed else None,
        'unit_addition_permits': [{
            'permit_number': p['permit_number'], 'status': p['status'], 'filed': p['filed'],
            'from_units': _as_float(p['existing_units']), 'to_units': _as_float(p['proposed_units']),
            'description': p['description'][:120],
        } for p in additions],
        'dataset_url': DBI_URL,
    }


def summarize_rent_board(rows):
    if rows is None:
        return None
    latest = rows[0] if rows else None
    return {
        'submissions': len(rows),
        'block_address': latest['block_address'] if latest else None,
        'latest_unit_count': _as_float(latest['unit_count']) if latest else None,
        'latest_signed': latest['signed'] if latest else None,
        'dataset_url': RENTBOARD_URL,
    }


def city_record(prop):
    """Live city record bundle for one seeded property. None when fully unreachable."""
    addr = prop.get('address') or {}
    dbi = dbi_permits(addr.get('street_number', ''), addr.get('street_name', ''),
                      addr.get('street_suffix', ''))
    rb = rent_board_block(prop.get('block_address', ''))
    if dbi is None and rb is None:
        return None
    return {'dbi': summarize_dbi(dbi), 'rent_board': summarize_rent_board(rb)}


def fred_rate():
    """Latest weekly 30-year fixed mortgage rate. Returns (rate_pct, week_ending) or None."""
    def fetch():
        text = _http_get(FRED_URL).decode('utf-8', 'replace')
        rows = [line.split(',', 1) for line in text.strip().splitlines()]
        rows = [(d.strip(), v.strip()) for d, v in rows[1:] if len((d, v)) == 2] if rows else []
        for date, value in reversed(rows):
            if value and value != '.':
                return (float(value), date)
        return None
    r = _cached('fred:MORTGAGE30US', fetch)
    if r is None:
        return None
    return (r[0], r[1])
