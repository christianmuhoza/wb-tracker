from api import q, import_bidders_from_notice

if __name__ == '__main__':
    notices = q("SELECT id FROM procurement_notices WHERE notice_type IN ('Contract Award','Award') OR status = 'Awarded'")
    print('notices', len(notices))
    summary = {'processed': 0, 'bidders_found': 0, 'bidders_inserted': 0, 'links_created': 0, 'errors': 0}
    for n in notices:
        nid = n['id']
        try:
            res = import_bidders_from_notice(nid, fetch_detail=False)
            summary['processed'] += 1
            summary['bidders_found'] += res.get('bidders_found', 0)
            summary['bidders_inserted'] += res.get('bidders_inserted', 0)
            summary['links_created'] += res.get('links_created', 0)
        except Exception as e:
            print('ERROR', nid, repr(e))
            summary['errors'] += 1
    print('SUMMARY', summary)
