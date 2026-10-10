import asyncio
import time
from collections import OrderedDict
from urllib.parse import quote
import httpx

class Wikipedia:
    def __init__(self, transport=None):
        self.http=httpx.AsyncClient(timeout=httpx.Timeout(12,connect=5),transport=transport,follow_redirects=False,
            headers={'User-Agent':'Daffo-Botz/3.1 (Wikipedia summary assistant)'})
        self.cache=OrderedDict()
        self.locks=[asyncio.Lock() for _ in range(16)]

    async def search(self, query, language='id'):
        query=query.strip()
        if not query or len(query)>250: raise ValueError('Topik Wikipedia wajib diisi, maksimal 250 karakter.')
        if language not in ('id','en'): raise ValueError('Bahasa wiki: id atau en.')
        key=(language,query.casefold())
        async with self.locks[hash(key)%16]:
            old=self.cache.get(key)
            if old and time.monotonic()-old[0]<1800: return old[1]
            try:
                r=await self.http.get(f'https://{language}.wikipedia.org/w/api.php',params={
                    'action':'query','format':'json','formatversion':2,'generator':'search','gsrsearch':query,
                    'gsrnamespace':0,'gsrlimit':1,'prop':'extracts|info','exintro':1,'explaintext':1,'inprop':'url'})
                r.raise_for_status()
                pages=r.json().get('query',{}).get('pages',[])
                if not pages: raise ValueError('Artikel Wikipedia tidak ditemukan. Coba kata kunci lebih spesifik.')
                page=pages[0]
                result={'title':page['title'],'extract':page.get('extract','')[:6500],
                        'url':f'https://{language}.wikipedia.org/wiki/'+quote(page['title'].replace(' ','_'),safe='')}
                if not result['extract']: raise ValueError('Ringkasan artikel kosong. Coba topik lain.')
            except (httpx.HTTPError,KeyError,TypeError) as exc:
                raise ValueError('Wikipedia belum dapat diakses. Coba lagi sebentar.') from None
            self.cache[key]=(time.monotonic(),result)
            while len(self.cache)>200:self.cache.popitem(last=False)
            return result

    async def close(self): await self.http.aclose()
