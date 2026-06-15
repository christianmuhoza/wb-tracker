"""
Import bidders/companies from contact_org field in awarded notices into Bidders table.
Run: python import_contact_org_bidders.py
"""

from api import db

if __name__ == '__main__':
    # Get all awarded notices with contact_org
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, contact_org, contact_name, contact_email, contact_phone, country, notice_date, contract_amount, currency, status
                FROM procurement_notices 
                WHERE (notice_type IN ('Contract Award', 'Award') OR status = 'Awarded')
                AND contact_org IS NOT NULL 
                AND TRIM(contact_org) <> ''
            """)
            notices = cur.fetchall()
    
    print(f'Found {len(notices)} awarded notices with contact_org')
    
    summary = {
        'processed': 0,
        'bidders_inserted': 0,
        'bidders_updated': 0,
        'links_created': 0,
        'links_updated': 0,
        'errors': 0
    }
    
    for notice in notices:
        nid = notice['id']
        contact_org = notice['contact_org'].strip()
        
        if not contact_org:
            continue
            
        try:
            with db() as conn:
                with conn.cursor() as cur:
                    # Check if bidder already exists
                    cur.execute("SELECT id FROM bidders WHERE lower(name) = lower(%s)", [contact_org])
                    existing = cur.fetchone()
                    
                    if existing:
                        bidder_id = existing['id']
                        # Update bidder with contact info if available
                        cur.execute("""
                            UPDATE bidders 
                            SET contact_name = COALESCE(NULLIF(contact_name, ''), %s),
                                contact_email = COALESCE(NULLIF(contact_email, ''), %s),
                                contact_phone = COALESCE(NULLIF(contact_phone, ''), %s),
                                country = COALESCE(NULLIF(country, ''), %s),
                                updated_at = NOW()
                            WHERE id = %s
                        """, [
                            notice.get('contact_name'),
                            notice.get('contact_email'),
                            notice.get('contact_phone'),
                            notice.get('country'),
                            bidder_id
                        ])
                        summary['bidders_updated'] += 1
                    else:
                        # Insert new bidder
                        cur.execute("""
                            INSERT INTO bidders (name, contact_name, contact_email, contact_phone, contact_org, country, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                            RETURNING id
                        """, [
                            contact_org,
                            notice.get('contact_name'),
                            notice.get('contact_email'),
                            notice.get('contact_phone'),
                            contact_org,
                            notice.get('country')
                        ])
                        bidder_id = cur.fetchone()['id']
                        summary['bidders_inserted'] += 1
                    
                    # Check if link already exists
                    cur.execute("SELECT id FROM bidder_awards WHERE bidder_id = %s AND notice_id = %s", [bidder_id, nid])
                    existing_link = cur.fetchone()
                    
                    # Determine if this bidder won the award
                    won = notice.get('status') in ('Awarded', 'Award', 'Contract Award')
                    
                    if existing_link:
                        # Update existing link
                        cur.execute("""
                            UPDATE bidder_awards 
                            SET won = %s, 
                                award_amount = %s, 
                                currency = %s, 
                                award_date = %s,
                                updated_at = NOW()
                            WHERE id = %s
                        """, [
                            won,
                            notice.get('contract_amount'),
                            notice.get('currency'),
                            notice.get('notice_date'),
                            existing_link['id']
                        ])
                        summary['links_updated'] += 1
                    else:
                        # Create new link
                        cur.execute("""
                            INSERT INTO bidder_awards (bidder_id, notice_id, won, award_amount, currency, award_date, role, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        """, [
                            bidder_id,
                            nid,
                            won,
                            notice.get('contract_amount'),
                            notice.get('currency'),
                            notice.get('notice_date'),
                            None
                        ])
                        summary['links_created'] += 1
                    
                    conn.commit()
            
            summary['processed'] += 1
            
        except Exception as e:
            print(f'ERROR processing notice {nid}: {repr(e)}')
            summary['errors'] += 1
    
    print('SUMMARY:', summary)
