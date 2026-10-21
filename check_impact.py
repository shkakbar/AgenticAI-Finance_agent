import json

d = json.load(open('data/reports/latest_analysis.json'))
ia = d['sentiment_data'].get('impact_analysis', {})

print('KEYS:', list(ia.keys()))
print('\nCATEGORY IMPACT:', ia.get('category_impact'))
print('SUB-CLASS IMPACT:', ia.get('sub_class_impact'))
print('REGION IMPACT:', ia.get('region_impact'))

print('\n--- OPPOSING IMPACTS (Req 2: negative for one, positive for another) ---')
opp = ia.get('opposing_impacts', [])
print(f'count: {len(opp)}')
for o in opp[:3]:
    print('*', o['headline'][:90])
    for e in o['effects']:
        print(f"    {e['segment']:>10} {e['score']:+4d} | {e['why']}")

print('\n--- DELAYED IMPACTS (Req 3: hits in coming days/weeks) ---')
dl = ia.get('delayed_impacts', [])
print(f'count: {len(dl)}')
for x in dl[:6]:
    print(f"[{x['timing']:>5}] {x['segment']:>10} {x['score']:+4d} | {x['headline'][:60]} | {x['why']}")

print('\n--- SWEDEN TRANSMISSION (Req 4) ---')
print(json.dumps(ia.get('se_impact', {}), indent=2, ensure_ascii=False))