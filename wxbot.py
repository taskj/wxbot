# -*- coding: utf-8 -*-
#taskj的微信登陆爬虫程序
import os
import re
import requests
import time
import sys
import json
import subprocess
import xml.dom.minidom



##############################################
#requests库session对象方法
session = requests.session()
#定义发送的表头
headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:49.0) Gecko/20100101 Firefox/49.0'}
#微信验证码生成路径
qrimgpath = os.path.split(os.path.realpath(__file__))[0] + os.sep + 'wxqrimg.jpg'
#微信扫码状态
tip = 0

uuid = ''
base_url = ''
redirect_url = ''
base_request = {}
deviceid = 'e681117882270251'
contactlist = ''
my = []
#登陆微信参数
uin = ''
skey = ''
sid = ''
pass_ticket = ''
synckey = ''
info = ''
##############################################


#获取微信uuid函数，返回UUID值(string)
def getuuid():
	global uuid,session
	url = "https://login.wx.qq.com/jslogin"
	#请求UUID所需要的GET的5个参数
	params = {
		'appid':'wx782c26e4c19acffb',
		'redirect':'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage',
		'fun':'new',
		'lang':'zh_CN',
		'_':int(time.time())
	}
	#GET 5个参数请求上面地址
	response = session.get(url,params=params)
	#接收UUID服务器返回的数据
	#请求正常返回的数据:window.QRLogin.code = 200; window.QRLogin.uuid = "wfsAc0_PVg==(随机字符窜)";
	data = response.content.decode('utf-8')
	#正则表达式截取返回数据的值
	regx = r'window.QRLogin.code = (\d+); window.QRLogin.uuid = "(\S+?)"'
	#截取服务器返回状态和UUID
	rd = re.search(regx,data)
	code = rd.group(1)
	uuid = rd.group(2)
	if code == '200':
		return True
	else:
		return False

#显示微信二维码函数
def showqrimg():
	global tip
	#网址拼接uuid，服务器返回用于登陆的二维码
	url = 'https://login.weixin.qq.com/qrcode/' + uuid
	#get请求服务器
	response = session.get(url)
	tip = 1
	#将服务器返回的二维码图片写入文件
	with open(qrimgpath,'wb') as qrimg:
		qrimg.write(response.content)
		qrimg.close()
	os.startfile(qrimgpath)
	print('[*]获取二维码成功...')
	print('[*]请扫描二维码登陆微信...')


#检测微信的登陆状态
def waitlogin():
	global tip,base_url,redirect_url
	#检测登陆状态的url,带登陆状态tip,uuid,time三个参数
	url = 'https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?tip=%s&uuid=%s&_=%s' %(tip,uuid,int(time.time()))
	#get请求服务器检测登陆状态
	response = session.get(url)
	#接收服务器返回的状态码，未登陆状态码408
	data = response.content.decode('utf-8')
	#正则表达式截取状态码
	regx = r'window.code=(\d+);'
	#获得状态码
	pm = re.search(regx,data)
	#状态码放入变量
	code = pm.group(1)

	#判断微信的登陆状态
	if code == '201':#已经扫描
		print('[*]扫描成功，请在手机上确认登陆')
		tip = 0
	elif code == '200':#登陆成功
		print('[*]扫描成功，正在登陆...')
		#接收登陆成功后返回的重定向地址
		regx = r'window.redirect_uri="(\S+?)";'
		pm = re.search(regx,data)
		redirect_url = pm.group(1) + '&fun=new&version=v2'
		base_url = redirect_url[:redirect_url.rfind('/')]
	elif code == '408':
		pass

	return code

def login():
	global skey,uin,sid,pass_ticket,base_request
	response = session.get(redirect_url)
	#服务器返回xml数据
	data = response.content.decode('utf-8')
	#以下开始解析服务器返回XML格式数据，获取skey,wxuin,wxsid,pass_ticket 4个参数
        # <error>
        #     <ret>0</ret>
        #     <message>OK</message>
        #     <skey>xxx</skey>
        #     <wxsid>xxx</wxsid>
        #     <wxuin>xxx</wxuin>
        #     <pass_ticket>xxx</pass_ticket>
        #     <isgrayscale>1</isgrayscale>
        # </error>
	#转换成字符窜格式
	doc = xml.dom.minidom.parseString(data)
	root = doc.documentElement
	
	#遍历
	for node in root.childNodes:
		if node.nodeName == 'skey':
			skey = node.childNodes[0].data
		elif node.nodeName == 'wxsid':
			sid = node.childNodes[0].data
		elif node.nodeName == 'wxuin':
			uin = node.childNodes[0].data
		elif node.nodeName == 'pass_ticket':
			pass_ticket = node.childNodes[0].data

	base_request = {
		'uin':uin,
		'sid':sid,
		'skey':skey,
		'deviceid':deviceid,	
	}
	return True

#登陆成功后初始化微信
def wxinit():
	url = base_url + \
        '/webwxinit?pass_ticket=%s&skey=%s&r=%s' % (
            pass_ticket, skey, int(time.time()))
	params = {
		'BaseRequest':base_request
	}
	h = headers
	h['ContentType'] = 'application/json; charset=UTF-8'
	#带参数post
	response = session.post(url,data=json.dumps(params),headers=h)
	#接收微信初始化返回的json数据
	data = response.content.decode('utf-8')
	global contactlist,my,synckey,info
	#读取json
	info = json.loads(data)
	contactlist = info['ContactList']
	my = info['User']
	synclist = []
	for item in info['SyncKey']['List']:
		synclist.append('%s_%s' % (item['Key'], item['Val']))
		synckey = '|'.join(synclist)
	errmsg = info['BaseResponse']['ErrMsg']
	ret = info['BaseResponse']['Ret']
	if ret != 0:
		return False
	return True

#获取微信的联系人
def getcontact():
	url = base_url + \
		'/webwxgetcontact?pass_ticket=%s&skey=%s&r=%s' % (
		pass_ticket, skey, int(time.time()))
	response = session.get(url)
	#接收服务器返回的联系人json数据
	data = response.content.decode('utf-8')
	#读取json
	info = json.loads(data)
	#获取好友列表
	memberlist = info['MemberList']
	#倒序遍历好友列表
	for i in range(len(memberlist)-1,-1,-1):
		member = memberlist[i]
		if member['VerifyFlag'] & 8 != 0: #公众号/服务号
			memberlist.remove(member)
		elif member['UserName'].find('@@') != -1: #群聊
			memberlist.remove(member)
		elif member['UserName'] == my['UserName']: #自己
			memberlist.remove(member)

	return memberlist

#开启微信状态通知
def wx_notify():
	url = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxstatusnotify?lang=zh_CN&pass_ticket=%s' % (pass_ticket)
	params = {
		'BaseRequest':base_request,
		'Code': 3,
		'FromUserName':my['UserName'],
		'ToUserName':my['UserName'],
		'ClientMsgId': int(time.time()),
	}
	response = session.post(url,data=json.dumps(params),timeout=60)
	# {
	# "BaseResponse": {
	# "Ret": 0,
	# "ErrMsg": ""
	# }
	# ,
	# "MsgID": "5653817886651689149"
	# }
	data = response.content.decode('utf-8')
	jsons = json.loads(data)
	return jsons['BaseResponse']['Ret'] == 0

#检查消息更新
def checksync():
	url = 'https://webpush2.weixin.qq.com/cgi-bin/mmwebwx-bin/synccheck?&r=%s&sid=%s&uin=%s&deviceid=%s&synckey=%s&_=%s&skey=%s' % (int(time.time()),sid,uin,deviceid,synckey,int(time.time()),skey)
	response = session.get(url,timeout=60)
	#数据返回的格式:window.synccheck={retcode:"xxx",selector:"xxx"}
	data = response.content.decode('utf-8')
	#正则表达式截取selector的值
	regx = r'window.synccheck={retcode:"(\d+)",selector:"(\d+)"}'
	pm = re.search(regx,data)
	ret = pm.group(1)
	code = pm.group(2)
	#code值0:正常,2:新的消息

	return code == '2'

	return ret,code

	print(synckey)


	 
#接收最新微信消息
def syncmess():
	#请求消息的地址
	url = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxsync?sid=%s&skey=%s&lang=zh_CN' % (sid,skey)
	#需要post的参数
	params = {
		'BaseRequest':base_request,
	  	'SyncKey': info['SyncKey'],
     	'rr': ~int(time.time()),
	}
	#post请求服务器
	response = session.post(url,data=json.dumps(params),timeout=60)
	data = response.content.decode('utf-8')
	# {
	# "BaseResponse": {
	# "Ret": 0,
	# "ErrMsg": ""
	# }
	jsons = json.loads(data)
	#更新synckey
	synclist = []
	for item in jsons['SyncKey']['List']:
		synclist.append('%s_%s' % (item['Key'], item['Val']))
		synckey = '|'.join(synclist)
	#接收到的json发送到handlemess()函数处理
	handlemess(jsons)



#获取昵称
def get_nick_name():
	pass



#处理消息
def handlemess(jsons):
	if not jsons:
		return

	for message in jsons['AddMsgList']:
		msg_type = message['MsgType']
		content = message['Content'].replace('&lt;', '<').replace('&gt;', '>')
		group_id = message['FromUserName']
		if msg_type == 1:
			time.sleep(3)
			print('有个人用户CALL你')


#程序的主函数
def main():
	print('[*]正在获取uuid...')
	if not getuuid():
		print('获取uuid失败')
		return
	print('[*]正在获取二维码...')
	showqrimg()
	time.sleep(1)

	#检测二维码的扫描状态
	while waitlogin() != '200':
		pass
	#登陆成功返回200状态码后删除二维码
	os.remove(qrimgpath)
	
	if not login():
		print('[*]登陆微信失败...')
		return
	#登陆成功，开始初始化微信
	print('[*]初始化微信中...')
	if not wxinit():
		print('[*]初始化微信失败')
		return
	#接收函数返回的数据
	print('[*]读取联系人信息中...')
	memberlist = getcontact()
	print('[*]读取联系人信息成功...')
	print('[*]您的通讯录共有%s位好友' % len(memberlist) )

	# for s in memberlist:
	print('昵称:%s,备注:%s,来自:%s, 签名:%s' % (s['NickName'],s['RemarkName'],s['Province']+s['City'], s['Signature']))
	print('--------------------------------------------------------------------------------------------------------------------------------------------------')
	print('[*]请求开启微信状态通知...')

	if wx_notify():
		print('[*]请求开启微信状态通知成功...')

	#获取检查消息的返回值，0无消息，2新消息
	print('[*]请求开启微信状态通知成功...')
	print('[*]回路监听微信消息中...')
	while True:
		time.sleep(1)
		#接收sync状态码
		if checksync():
			syncmess()
			
if __name__ == '__main__':
	print('---------------------------')
	print('|启动taskj的微信机器人程序|')
	print('---------------------------')
	time.sleep(2)
	main()



	