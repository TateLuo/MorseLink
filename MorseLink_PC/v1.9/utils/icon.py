from tkinter import *
import webbrowser
import time, datetime
import re
import base64
 
 
 
open_icon = open("logo.ico","rb") #qq.icon为你要放入的图标
b64str = base64.b64encode(open_icon.read())  #以base64的格式读出
open_icon.close()
write_data = "img=%s" % b64str
f = open("qq.py","w+")   #将上面读出的数据写入到qq.py的img数组中
f.write(write_data)
f.close() 