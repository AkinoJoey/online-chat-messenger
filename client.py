import socket
import sys
import asyncio
import aioconsole
import logging

class Client:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.address = '127.0.0.1'
        self.port = None
        self.status = None
        self.server_address = '127.0.0.1'
        self.server_port = 9005
    
    def connectServer(self):
        try:
            self.sock.settimeout(2)
            self.sock.connect((self.server_address,self.server_port))
        except OSError as e:
            print(e)
            sys.exit(1)
        
        try:
            user_name = input("--> Type in your name: ")
            self.sendUserData(user_name)
            
            service_type = self.promptServiceType()
            self.sendUserData(service_type)
            self.setStatus(service_type)
            
            chatRoom_name = self.promptChatRoomName()
                
            # ユーザーが参加者のときはmaxMemberを0に設定しておく
            maxMember = "0" if service_type == "2" else self.promptMaxMember()
            self.sendUserData(maxMember)
            
            self.setClientPortNumber()

            chatRoom_port =  self.getChatroomPort()
            self.makeChatClient(chatRoom_name, chatRoom_port)
            
        except Exception as e:
            print(e)
            
        finally:
            print('closing chat service')
            self.sock.close()
    
    def sendUserData(self, userdata):
        userdata_bytes = userdata.encode("utf-8")
        self.sock.send(len(userdata_bytes).to_bytes(2, "big"))
        self.sock.send(userdata_bytes)

    def promptServiceType(self):
        while True:
            service_type = input("--> Type in 1 if you want to make a new chat room. Type in 2 if you want to join in a chat room: ")
            if service_type == "1" or service_type == "2":
                return service_type
            else:
                print("Please type in 1 or 2")
    
    def setStatus(self,service_type):
        if service_type == "1":
            self.status = "host"
            
        else:
            self.status = "participant"
    
    def promptChatRoomName(self):
        while True:
            print(self.status)
            chatRoom_name = input("--> Type in the name of the chat room you want to make: ") if self.status == "host" else input("--> Type in the name of the chat room you want to join in: ")
            self.sendUserData(chatRoom_name)
            
            findChatRoom = int.from_bytes(self.sock.recv(2), "big")
            
            print(findChatRoom)
            
            if findChatRoom == 0:
                if self.status == "host":
                    print("The chat room name is already in use.")
                else:
                    print("You cannot join the chat room. It does not exist or is already full.")
            else:
                return chatRoom_name
    
    def promptMaxMember(self):
        while True:
            maxMember = input("--> Type in the maximum number of participants for your chat room: ")
            if maxMember.isdigit() and maxMember != "0":
                return maxMember
            else:
                print("Please type in a natural number.")
        
    def setClientPortNumber(self):
        while self.port == None:
            self.port = int.from_bytes(self.sock.recv(2), "big")     
            print("my port is {}".format(self.port))
    
    def getChatroomPort(self):
        chatRoom_port = None
        while True:
            chatRoom_port = int.from_bytes(self.sock.recv(2), "big")
            print("chat room port is {}".format(chatRoom_port))

            if chatRoom_port != None:
                return chatRoom_port
    
    def makeChatClient(self,chatRoom_name, chatRoom_port):
        chatClient = ChatClient(self.port,self.status,chatRoom_name,chatRoom_port)

class ChatClient:
    def __init__(self,port,status,chatRoom_name,chatRoom_port):
        self.sockForChat = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sockForChat.setblocking(False)
        self.address = '127.0.0.1'
        self.port = port
        self.status = status
        self.chatRoom_address = '127.0.0.1'
        self.chatRoom_port = chatRoom_port
        self.chatRoom_name = chatRoom_name
        self.sockForChat.bind((self.address, self.port))

        print('\nStart the new chat room "{}"'.format(self.chatRoom_name)) if self.status == "host" else print("Join in {}".format(self.chatRoom_name))
        
        if self.status == "participant":
            joinMessage = "{}:join".format(self.chatRoom_name)
            self.sockForChat.sendto(joinMessage.encode("utf-8"),(self.chatRoom_address, self.chatRoom_port))
        
        asyncio.run(self.startChat(),debug=True)

    async def startChat(self):
        try: 
            async with asyncio.TaskGroup() as tg:
                receveTask = tg.create_task(self.receveMessage())
                sendTask = tg.create_task(self.sendMessage(receveTask))
            
        except Exception as e:
            print("Error: " + str(e))
            self.sockForChat.close()
            
        finally:
            self.sockForChat.close()

    async def receveMessage(self):
        while True:
            loop = asyncio.get_running_loop()
            data, address = await loop.sock_recvfrom(self.sockForChat, 4096)
            
            if data:
                print(data.decode())    

            await asyncio.sleep(0.1)
    

    async def sendMessage(self,receveTask):
        while True:
            message = await aioconsole.ainput()
            leave = False

            if message == "bye":
                leave = await self.confirmLeaveChatroom()

            if leave == True:
                await self.leaveChatroom(receveTask)
                break
            else:
                messageSize = len(message)
                prefix = "{}:{}:{}".format(self.chatRoom_name, messageSize, message)
                loop = asyncio.get_running_loop()
                await loop.sock_sendto(self.sockForChat, prefix.encode("utf-8"), (self.chatRoom_address, self.chatRoom_port))
                print()
                print("\nYou: {}".format(message))
            
            await asyncio.sleep(0.1)
    
    async def confirmLeaveChatroom(self):
        while True:
            confirmMessage = await aioconsole.ainput("--> Do you want to leave the chat room? Type in Yes or No: ")
            if confirmMessage == "Yes":
                return True
            elif confirmMessage == "No":
                return False
            else:
                confirmMessage = print("Please tyep in Yes or No")
    
    async def leaveChatroom(self,receveTask):
        receveTask.cancel()
        stringtoLeave = "real-Bye-Bye"
        messageSize = len(stringtoLeave)
        prefix = "{}:{}:{}".format(self.chatRoom_name, messageSize, stringtoLeave)
        loop = asyncio.get_running_loop()
        await loop.sock_sendto(self.sockForChat, prefix.encode("utf-8"), (self.chatRoom_address, self.chatRoom_port))
        
class Main:
    client = Client()
    client.connectServer()
    
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    Main()

