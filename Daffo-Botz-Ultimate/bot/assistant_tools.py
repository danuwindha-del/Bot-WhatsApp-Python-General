"""Restricted tools. Privileged/state-changing commands remain explicit user actions."""
import json
from bot.calculator import calculate

READ_ONLY={'ping','statusbot','runtime','botinfo','stats','totalfitur','totaluser','tes','speed',
           'owner','creator','script','sc','kbbi','translate','tr','doa','calc','kalkulator','wiki','wikipedia',
           'truth','dare','pilih','angka','cekiq','cekcantik','cantikcek','gantengcek','ceksifat','cekkhodam',
           'stress','quotebucin','sadboy','jadian','dimanakah','carabalikan'}

def function(name,description,properties,required):
    return {'type':'function','function':{'name':name,'description':description,
        'parameters':{'type':'object','properties':properties,'required':required,'additionalProperties':False}}}

class CaptureContext:
    def __init__(self,ctx,command,args):
        self.original=ctx;self.command_name=command;self.command_args=args;self.text='.'+command+' '+args;self.outputs=[]
    def __getattr__(self,name):return getattr(self.original,name)
    async def reply(self,text):self.outputs.append(str(text)[:6000])

class Toolbox:
    schemas=[
        function('calculate','Hitung operasi matematika secara akurat; persen adalah angka/100.',{'expression':{'type':'string'}},['expression']),
        function('wikipedia','Cari dan baca ringkasan Wikipedia dengan URL sumber.',{'query':{'type':'string'},'language':{'type':'string','enum':['id','en']}},['query']),
        function('bot_command','Jalankan fitur baca saja atau dapatkan petunjuk command eksplisit untuk aksi lain.',{'command':{'type':'string'},'args':{'type':'string'}},['command']),
        function('list_commands','Lihat command yang tersedia serta status implementasinya.',{'query':{'type':'string'}},[]),
    ]
    def __init__(self,bot,ctx=None):self.bot=bot;self.ctx=ctx

    async def execute(self,call):
        try:
            f=call['function'];args=json.loads(f.get('arguments','{}'))
            if not isinstance(args,dict) or len(json.dumps(args))>1800:raise ValueError('Argumen tool tidak valid.')
            name=f['name']
            if name=='calculate':
                return {'ok':True,'text':calculate(args['expression'])}
            if name=='wikipedia':
                r=await self.bot.wiki.search(args['query'],args.get('language','id'))
                return {'ok':True,**r,'text':r['title']+'\n'+r['extract']+'\n'+r['url']}
            if name=='list_commands':
                q=str(args.get('query','')).lower()
                items=[x for x in self.bot.command_catalog() if q in x['name']]
                return {'ok':True,'total':len(items),'text':'\n'.join(x['usage']+' — '+x['status']+(' (OFF)' if not x['enabled'] else '') for x in items)[:6500]}
            if name=='bot_command':
                command=str(args['command']).lower().lstrip('.');value=str(args.get('args',''))
                if command not in self.bot.router:raise ValueError('Command tidak terdaftar.')
                if command not in READ_ONLY or self.ctx is None:
                    return {'ok':False,'text':'Belum dijalankan. Pengguna perlu mengetik command eksplisit: .'+command+' '+value}
                ctx=CaptureContext(self.ctx,command,value)
                await self.bot.execute_command(ctx,command,value)
                return {'ok':True,'text':'\n'.join(ctx.outputs) or 'Command selesai tanpa keluaran teks.'}
            raise ValueError('Tool tidak dikenal.')
        except (ValueError,KeyError,TypeError):
            return {'ok':False,'text':'Tool gagal atau argumennya tidak valid. Jangan mengklaim berhasil; sarankan command langsung.'}
