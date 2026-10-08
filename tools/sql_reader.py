"""Read mysqldump INSERT statements without running SQL or using a database."""
import re,pathlib
def load_sql(path):
 s=pathlib.Path(path).read_text(encoding="utf-8-sig")
 tables={}
 for m in re.finditer(r'INSERT INTO `(wp_(?:posts|postmeta|terms|term_taxonomy|term_relationships))` \((.*?)\) VALUES\s*',s):
  table,cols=m.group(1),re.findall(r'`([^`]+)`',m.group(2)); i=m.end(); rows=[]
  while True:
   while s[i].isspace() or s[i]==',': i+=1
   if s[i]!='(': break
   i+=1; row=[]
   while True:
    while s[i].isspace(): i+=1
    if s[i]=="'":
     i+=1; out=[]
     while True:
      c=s[i]; i+=1
      if c=='\\':
       c=s[i]; i+=1; out.append({'n':'\n','r':'\r','t':'\t','0':'\0','Z':'\x1a'}.get(c,c))
      elif c=="'":
       if s[i]=="'": out.append("'"); i+=1
       else: break
      else: out.append(c)
     val=''.join(out)
    else:
     j=i
     while s[i] not in ',)': i+=1
     v=s[j:i].strip(); val=None if v=='NULL' else int(v) if re.fullmatch(r'-?\d+',v) else v
    row.append(val)
    while s[i].isspace(): i+=1
    c=s[i]; i+=1
    if c==')': break
   assert len(cols)==len(row),(table,len(cols),len(row))
   rows.append(dict(zip(cols,row)))
  tables.setdefault(table,[]).extend(rows)
 return tables
