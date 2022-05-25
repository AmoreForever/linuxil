from .. import loader, utils  # pylint: disable=relative-beyond-top-level 
import logging 
from requests import post 
import io 
 
logger = logging.getLogger(__name__) 
 
@loader.tds 
class x0Mod(loader.Module): 
 """LINUXIL uploader server""" 
 strings = { 
  "name": "LINUXILx0" 
 } 
 
 async def client_ready(self, client, db): 
  self.client = client 
  
  
 @loader.sudo 
 async def installcmd(self, message): 
  await message.edit("<b>👾 Загрузка файла на сервер x0...</b>") 
  reply = await message.get_reply_message() 
  if not reply: 
   await message.edit("<b>❗ А где реплай</b>") 
   return 
  media = reply.media 
  if not media: 
   file = io.BytesIO(bytes(reply.raw_text, "utf-8")) 
   file.name = "txt.txt" 
  else: 
   file = io.BytesIO(await self.client.download_file(media)) 
   file.name = reply.file.name if reply.file.name else  reply.file.id+reply.file.ext 
  try: 
   x0at = post('https://x0.at', files={'file': file}) 
  except ConnectionError as e: 
   await message.edit(ste(e)) 
   return 
  url = x0at.text 
  output = f' 🪁<code>.dlmod {url}</code>' 
  await message.edit(output)
