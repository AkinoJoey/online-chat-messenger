import socket
import sys

class Client:
    
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = '127.0.0.1'
        self.server_port = 9005
        self.address = '127.0.0.1'
        self.port = 9998
        
    def protocol_header(username_length, service_type_length, chatroom_name_length, maxMember_length):
        return username_length.to_bytes(2, "big") + service_type_length.to_bytes(2, "big") + chatroom_name_length.to_bytes(2, "big") + maxMember_length.to_bytes(2, "big")
    
    def startChat(self,chatRoom_name):
        sockForChat = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        chatroom_address = '127.0.0.1'
        chatroom_port = 9002
        
        sockForChat.bind((self.address, self.port))
        print('\nStart the new chat room "{}"'.format(chatRoom_name))
        
        while True:
            try:
                message = input("You: ").encode("utf-8")
                sockForChat.sendto(message, (chatroom_address, chatroom_port))
                
                sockForChat.settimeout(2)
                data, address = sockForChat.recvfrom(4096)
                print("{}: {}".format(address, data.decode()))
            
            except TimeoutError as e:
                print(e)
                sockForChat.close()
            
                
    def connectServer(self):
        
        try:
            self.sock.settimeout(2)
            self.sock.connect((self.server_address,self.server_port))
        except socket.error as e:
            print(e)
            sys.exit(1)
        
        try:
            user_name = input("--> Type in your name: ")
            user_name_bytes = user_name.encode("utf-8")
            
            while True:
                service_type = input("--> Type in 1 if you want to make a new chat room. Type in 2 if you want to join in a chat room: ")
                if service_type == "1" or service_type == "2":
                    break
                else:
                    "Please type in 1 or 2"
            
            service_type_bytes = service_type.encode("utf-8")
            
            chatRoom_name = input("--> Type in the name of the chat room you want to make: ") if service_type == "1" else input("--> Type in the name of the chat room you want to join in: ")
            chatRoom_name_bytes = chatRoom_name.encode("utf-8")
            
            # ユーザーが参加者のときは0に設定しておく
            promptMaxMember = "0" if service_type == "2" else input("--> Type in  the maximum number of participants for your chat room: ")
            promptMaxMember_bytes = promptMaxMember.encode("utf-8")
            
            header = Client.protocol_header(len(user_name_bytes), len(service_type_bytes),len(chatRoom_name_bytes),len(promptMaxMember_bytes))
            
            self.sock.send(header)
            self.sock.send(user_name_bytes)
            self.sock.send(service_type_bytes)
            self.sock.send(chatRoom_name_bytes)
            self.sock.send(promptMaxMember_bytes)
            
            Client.startChat(self,chatRoom_name)
            
        except(TimeoutError):
            print("Socket timeout.")
            
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

    