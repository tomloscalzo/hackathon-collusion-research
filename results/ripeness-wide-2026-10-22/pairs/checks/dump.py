import json
d=json.load(open(r'<local>\hackathon\work_scratch\wide\pairs_out\tables.json',encoding='utf8'))
seen=[]
for k,v in d.items():
    kind,a,b=k.split('__')
    print('==',k)
    print('   ', b, v['col_levels'])
    for rl,row in zip(v['row_levels'],v['values']):
        print('  %s=%-6s'%(a,rl), ' '.join('%.3f'%x for x in row))
