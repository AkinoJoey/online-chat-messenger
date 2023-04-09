import socket
import sys
import asyncio
import aioconsole

class Client:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sockForChat = None
        self.chatRoom_address = None
        self.chatRoom_port = None
        self.server_address = '127.0.0.1'
        self.server_port = 9005
        self.address = '127.0.0.1'
        self.port = None
        self.status = None
        self.joinChatroom = False
        
    def setClientPortNumber(self):
        while self.port == None:
            self.port = int.from_bytes(self.sock.recv(2), "big")     
            print("my port is {}".format(self.port))
    
    def setChatroomPortNumber(self):
        while self.chatRoom_port == None:
            self.chatRoom_port = int.from_bytes(self.sock.recv(2), "big")
            print("chat room port is {}".format(self.chatRoom_port))
    
    def sendUserData(self, userdata):
        userdata_bytes = userdata.encode("utf-8")
        self.sock.send(len(userdata_bytes).to_bytes(2, "big"))
        self.sock.send(userdata_bytes)

    async def sendMessage(self,receveTask):
        while self.joinChatroom == True:
            message = await aioconsole.ainput()
            loop = asyncio.get_running_loop()
            await loop.sock_sendto(self.sockForChat, message.encode("utf-8"), (self.chatroom_address, self.chatRoom_port))
            print()
            print("\nYou: {}".format(message))
            await asyncio.sleep(0.1)

            if message == "bye":
                await self.leaveChatroom(receveTask)

    async def receveMessage(self):
        while True:
            loop = asyncio.get_running_loop()
            data, address = await loop.sock_recvfrom(self.sockForChat, 4096)
            if data:
                print(data.decode())    
            await asyncio.sleep(0.1)
                
    async def leaveChatroom(self,receveTask):
        while True:
            confirmMessage = await aioconsole.ainput("--> Do you want to leave the chat room? Type in Yes or No: ")
            if confirmMessage == "Yes":
                self.joinChatroom = False
                receveTask.cancel()
                break
            elif confirmMessage == "No":
                break
            else:
                confirmMessage = print("Please tyep in Yes or No")

    async def main(self):
        try: 
            async with asyncio.TaskGroup() as tg:
                receveTask = tg.create_task(self.receveMessage())
                sendTask = tg.create_task(self.sendMessage(receveTask))
            
        except Exception as e:
            print("Error: " + str(e))
            self.sockForChat.close()
            
        finally:
            self.sockForChat.close()

    def startChat(self,chatRoom_name):
        self.sockForChat = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sockForChat.setblocking(False)
        self.chatroom_address = '127.0.0.1'
        self.joinChatroom = True
        
        self.sockForChat.bind((self.address, self.port))
        print('\nStart the new chat room "{}"'.format(chatRoom_name))

        asyncio.run(self.main(),debug=True)

    def promptServiceType(self):
        while True:
            service_type = input("--> Type in 1 if you want to make a new chat room. Type in 2 if you want to join in a chat room: ")
            if service_type == "1" or service_type == "2":
                return service_type
            else:
                print("Please type in 1 or 2")
                
    def setStatus(self,service_type):
        if service_type == "1":
            self.status == "host"
            
        else:
            self.status == "participant"
            
    def promptChatRoomName(self):
        while True:
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
            self.setChatroomPortNumber()

            self.startChat(chatRoom_name)
            
        except Exception as e:
            print(e)
            
        finally:
            print('closing chat service')
            self.sock.close()
                    
            
class Main:
    client = Client()
    client.connectServer()
    
    
if __name__ == '__main__':
    Main()

