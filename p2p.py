# sudo ifconfig lo0 alias 127.0.0.2 up     - нужно ввести для создания виртулаьного IP(чтобы я могла ввести с клавиатуры IP)

import socket, threading

my_name = input("Введите ваше имя: ")
my_ip = input("Введите ваш IP: ")
my_udp_port = int(input("Введите ваш UDP порт: "))
my_tcp_port = int(input("Введите ваш TCP порт: "))

# Широковещательный крик (broadcast) хорошо работает только тогда, когда все в сети заранее договорились слушать один и тот же стандартный порт.
neighbr_ip = input("\nВведите IP друга: ")
neighbr_udp_port = int(input("Введите UDP порт друга: "))

print(f"\n~~~~~~~~~ Привет {my_name}. Твой IP-адрес: {my_ip} ~~~~~~~~~")

# В этот момент узел резервирует указанный UDP-порт для прослушивания эфира.
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) #задали наш юдп соккет
udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)#(где(у меня это уровень интерфейса), что, вкл/выкл)
udp_sock.bind((my_ip, my_udp_port))#привязка к адресу(bind)

my_info = f"{my_name}:{my_tcp_port}"
info_encode = my_info.encode('utf-8')
message = bytes([3, len(info_encode)]) + info_encode
udp_sock.sendto(message, (neighbr_ip, neighbr_udp_port))
print("UDP пакет отправлен")

neighbrs = {} #для сохранения соседей(типо словарик)

def listen_udp(): # типо стоит с блокнотом и записывает пролетающие мимо пакеты
   while True:
     data, addr = udp_sock.recvfrom(1024) #ждём сообщение из сети
     sender_ip = addr[0]
     sender_port = addr[1]
     if sender_ip == my_ip: #если это наше сообщение, то игнорим
       continue
     # 1[0] - это тип, 2[1] - это размер, 3 - придуманый мной тип
     if data[0] == 3: # правило 3 - подключился новый пользователь
       name_length = data[1]
       sender_name = data[2 : 2 + name_length].decode('utf-8') #[начало отсчёта : конечная позиция]
       friend_name, friend_tcp_port = sender_name.split(":")


       if not sender_ip in neighbrs:
        neighbrs[sender_ip] = (friend_name, int(friend_tcp_port))
        # Записываем того же друга под локальным адресом, чтобы TCP-сервер его узнал
        neighbrs['127.0.0.1'] = (friend_name, int(friend_tcp_port))
        print(f"\n [+] Найден новый узел {friend_name} : {friend_tcp_port}")
        udp_sock.sendto(message, (sender_ip, sender_port))
     
tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)  # SOCK_STREAM как единый, непрерывный поток (stream) данных 
tcp_server.bind((my_ip, my_tcp_port))

tcp_server.listen(5) # режим ожидания(как будто на телефонной линии весят 5 чел)

def helper_client(conn, addr): #выводят входящий текст на экран
  while True:
    try:
      data = conn.recv(1024)
      if not data: #если пусто, значит разорвали соеденение
        break
      
      text = data.decode('utf-8')
      # Пытаемся достать кортеж (Имя, Порт). Если IP нет в словаре, вернется строка "Неизвестный"
      friend_data = neighbrs.get(addr[0], ("Неизвестный", 0)) 
      friend_name = friend_data[0]

      print(f"\n [{friend_name} - {addr[0]}] : {text}")
    except Exception as e:
      print(f"Скрытая ошибка: {repr(e)}") # Печатаем ошибку прямо здесь, пока она существует!
      break

  print(f"\nСоединение с {addr} разорвано ") 
  conn.close()

udp_thread = threading.Thread(target=listen_udp, daemon=True) #прослушивает и записывает IP адреса новых соседей (UDP-разведчик)
udp_thread.start()
# щас будет кабинетик у моего тсп-секретаря
def listen_tcp(): # TCP-секретарь
  while True: # пока тсп ждёт звонка
    # Серверная часть (прием)
    client_sock, client_addr = tcp_server.accept()# принять подключение(accept обычно возвращает новый сокет + IP и порт)
    print(f"\n[TCP] установлено соединение с {client_addr}")

    # чтение сообщений из client_sock
    t = threading.Thread(target=helper_client, args= (client_sock, client_addr)) #наняла секретрю помощника   
    t.start()

tcp_thread= threading.Thread(target=listen_tcp, daemon=True) #принимает входящие тсп звонки
tcp_thread.start()

while True:
  text = input("Введите ваше сообщение: ")

  for find_ip in neighbrs: #проходим по всем найденным ip-адресам
    try:
      send_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP) #создали новый сокет-клиент
      send_sock.connect((find_ip, neighbrs[find_ip][1])) #подключились к соседу. Клиентская часть (отправка)
      send_sock.send(text.encode('utf-8'))
      send_sock.shutdown(socket.SHUT_RDWR)
      send_sock.close()

    except Exception as e:
      print(f"Не удалось отправить сообщение на {find_ip}")
      
