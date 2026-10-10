"""Isolated subprocess: reject private/loopback DNS results on every socket connection."""
import ipaddress
import socket
import sys
from pathlib import Path
import yt_dlp
from bot.media import validate_url

original=socket.getaddrinfo
def public_dns(host,*args,**kwargs):
    records=original(host,*args,**kwargs)
    if any(not ipaddress.ip_address(row[4][0]).is_global for row in records):
        raise OSError('Private network target denied')
    return records
socket.getaddrinfo=public_dns

def main():
    url=validate_url(sys.argv[1]);out=Path(sys.argv[2]);audio=sys.argv[3]=='audio'
    limit=max(10,min(int(sys.argv[4]) if len(sys.argv)>4 else 32,250))
    def guard(status):
        if status.get('downloaded_bytes',0)>limit*1024*1024:raise ValueError('Size limit')
    options={'outtmpl':str(out/'source.%(ext)s'),'noplaylist':True,'quiet':True,'no_warnings':True,
             'proxy':'','socket_timeout':15,'retries':2,'fragment_retries':2,'concurrent_fragment_downloads':1,
             'max_filesize':limit*1024*1024,'cachedir':False,'progress_hooks':[guard],
             'allowed_extractors':['youtube.*','tiktok.*','instagram.*'],
             'format':'bestaudio/best' if audio else 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]',
             'merge_output_format':'mp4','hls_prefer_native':True,
             'match_filter':yt_dlp.utils.match_filter_func('duration <= 600 & !is_live')}
    with yt_dlp.YoutubeDL(options) as dl:dl.download([url])
if __name__=='__main__':main()
