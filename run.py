import requests
import json
import sys
from tokens import Token
from constants import Timeout, HiMsg

#type: 0 - user, 1 - admin, 2 - banned
#user: {'id' : id, 'type' : type, 'username' : username}
#users: {id : user}

def markdownMessage(text):
	return {'command' : 'sendMessage', 'parse_mode' : 'Markdown', 'text' : text}

def textMessage(text):
	return {'command' : 'sendMessage', 'text' : text}

def readlines(f):
	res = f.readlines()
	for i in range(len(res)):
		res[i] = res[i][:len(res[i]) - 1]
	return res

def intToStrDict(d):
	return {str(x[0]) : x[1] for x in d.items()}

def strToIntDict(d):
	return {int(x[0]) : x[1] for x in d.items()}

class TelegramBot:
	def load(self):
		try:
			f = open(self.dataFilename, 'r')
		except:
			return
		x = readlines(f)
		try:
			self.offsetId = int(x[0])
			self.users = strToIntDict(json.loads(x[1]))
			for userId in self.users:
				if (self.users[userId]['type'] == 1):
					self.admins.append(userId)
			self.whoSent = strToIntDict(json.loads(x[2]))
			self.msgProb = strToIntDict(json.loads(x[3]))
		except:
			print("LoadError")
			sys.exit(1)

	def save(self):
		f = open(self.dataFilename, 'w')
		f.write(str(self.offsetId) + '\n')
		f.write(json.dumps(intToStrDict(self.users)) + '\n')
		f.write(json.dumps(intToStrDict(self.whoSent)) + '\n')
		f.write(json.dumps(intToStrDict(self.msgProb)) + '\n')

	def getUsername(self, user):
		if ('title' in user):
			return user['title']

		if ('username' in user):
			return user['username']

		fn = ('first_name' in user)
		sn = ('second_name' in user)
		if ((not fn) and (not sn)):
			return 'id' + str(user['id'])

		username = ''
		if (fn):
			username += user['first_name']
			if (sn):
				username += ' '
		if (sn):
			username += user['second_name']

		return username

	def __init__(self, token, dataFilename, logsFilename):
		self.token = token
		self.url = 'https://api.telegram.org/bot' + self.token + '/'
		self.users = {}
		self.admins = []
		self.whoSent = {}
		self.usrProb = {}
		self.msgProb = {}
		self.offsetId = -1
		self.dataFilename = dataFilename
		self.logsFilename = logsFilename
		self.load()

	def updateOffsetId(self, result):
		if (result):
			self.offsetId = result[-1]['update_id'] + 1

	def getUpdates(self):
		data = {'timeout': Timeout, 'offset': self.offsetId}
		response = requests.get(self.url + 'getUpdates', params = data)
		jsonResponse = response.json()
		if ('result' in jsonResponse):
			self.updateOffsetId(jsonResponse['result'])
			return jsonResponse['result']
		else:
			print("Can't get messages")
			print(jsonResponse)
			sys.exit(1)

	def addUser(self, user):
		self.users[user['id']] = {
			'id': user['id'],
			'type': 0,
			'probName' : 'no problem'
		}

	def sendCommand(self, responseElement, chatId):
		command = responseElement['command']
		responseElement.pop('command')
		params = responseElement
		params['chat_id'] = chatId
		response = requests.post(self.url + command, data = params)
		jsonResponse = response.json()
		if ('result' in jsonResponse):
			return jsonResponse['result']
		else:
			print("Can't send command")
			print(jsonResponse)
			sys.exit(1)

	def handleUpdate(self, update):
		if ('message' not in update):
			return
		f = open(self.logsFilename, 'a')
		f.write(json.dumps(update, indent = 4) + '\n\n\n')

		message = update['message']
		chat = message['chat']
		userId = chat['id']
		if (userId not in self.users):
			self.addUser(chat)
		user = self.users[userId]

		if ('text' in message):
			if (user['type'] == 0):
				#default user
				if (message['text'] == '/start'):
					self.sendCommand(markdownMessage(HiMsg), userId)
					return

				params = message['text'].split()
				if (params[0] == '/select' or params[0] == '/newtask'):
					if (len(params) >= 2):
						user['probName'] = ' '.join(params[1:])
					else:
						user['probName'] = 'no problem'
					self.sendCommand(markdownMessage("Название задачи: " + user['probName']), userId)
					return

				text = '*' + self.getUsername(chat) + ' (' + user['probName'] + ')' + '*\n' + message['text']
				for adminId in self.admins:
					resp = self.sendCommand(markdownMessage(text), adminId)
					self.whoSent[resp['message_id']] = userId
					self.msgProb[resp['message_id']] = user['probName']

			if (self.users[userId]['type'] == 1):
				if ('reply_to_message' in message):
					msgId = message['reply_to_message']['message_id']
					if (msgId not in self.whoSent):
						pass
					else:
						rabotyagaId = self.whoSent[msgId]
						if (message['text'] == '/op1'):
							self.users[rabotyagaId]['type'] = 1
							self.sendCommand(markdownMessage('op 1'), rabotyagaId)
							return
						if (message['text'] == '/op0'):
							self.users[rabotyagaId]['type'] = 0
							self.sendCommand(markdownMessage('op 0'), rabotyagaId)
							return
						if (message['text'] == '/op2'):
							self.users[rabotyagaId]['type'] = 2
							self.sendCommand(markdownMessage('Вам бан'), rabotyagaId)
							return

						text = '*' + self.getUsername(message['from']) + ' (' + self.msgProb[msgId] + ')' + '*\n' + message['text']
						self.sendCommand(markdownMessage(text), rabotyagaId)
						self.whoSent[message['message_id']] = rabotyagaId
						self.msgProb[message['message_id']] = self.msgProb[msgId]
				else:
					pass

	def go(self):
		updates = self.getUpdates()
		for update in updates:
			self.handleUpdate(update)
			self.save()

bot = TelegramBot(Token, 'saved', 'logs')

while (True):
	try:
		bot.go()
	except KeyboardInterrupt:
		break
