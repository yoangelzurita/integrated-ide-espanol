"""Autocompletado y referencia del lenguaje español de Integrated."""

SUGERENCIAS = [
    "al iniciar",
    "repetir siempre",
    "funcion encenderLuz",
    "fin funcion",
    "llamar encenderLuz",
    "fin si",
    "si",
    "si no",
    "variable entero =",
    "variable decimal =",
    "variable texto =",
    "variable verdadero o falso =",
    "asignar",
    "escribe",
    "escribir sin salto",
    "leer",
    "velocidad serie 115200",
    "configurar pin 13, salida",
    "configurar pin 2, entrada",
    "configurar pin 2, entrada con resistencia",
    "hacer que pin 13, encendido",
    "hacer que pin 13, apagado",
    "leer pin digital 2 en estado",
    "leer pin analógico A0 en valor",
    "escribir pwm pin 9 con 128",
    "esperar 1000",
    "esperar microsegundos 500",
    "repetir 10 veces",
    "mientras",
    "fin mientras",
    "romper",
    "continuar",
    "mapear valor de 0 a 1023 hacia 0 a 255 en resultado",
    "limitar valor entre 0 y 100",
    "aleatorio entre 0 y 100 en numero",
    "configurar led integrado",
    "encender led integrado",
    "apagar led integrado",
    "parpadear led integrado 500",
    # Red para ESP32 y ESP8266
    'wifi conectar "nombre" "clave"',
    'wifi nombre "MiRed"',
    'wifi clave "contraseña"',
    'wifi password "contraseña"',
    "wifi conectar nombre password",
    "wifi iniciar",
    'wifi crear punto de acceso "MiDispositivo" "clave1234"',
    'wifi crear punto de acceso "esp32_s2_mini_wifi" "12345678"',
    "wifi ip en direccion",
    "wifi mostrar ip",
    "wifi desconectar",
    'servidor iniciar 80',
    'servidor ruta "/" "Hola"',
    'servidor html "/" "<h1>Hola mundo</h1>"',
    'servidor html "/":',
    'contenido html "/":',
    "fin html",
    "fin contenido html",
    'servidor pagina "/" "index.html"',
    "servidor atender",
    # Proyectos reales
    "configurar ultrasonido trig 12 echo 13",
    "medir distancia en distancia",
    "configurar servo pin 9",
    "girar servo a 90",
    "configurar motor izquierdo pwm 5 in1 6 in2 7",
    "configurar motor derecho pwm 9 in1 10 in2 11",
    "motor izquierdo adelante 180",
    "motor derecho atras 150",
    "parar motores",
    "leer humedad suelo A0 en humedad",
    "leer temperatura lm35 A1 en temperatura",
    "leer luz A0 en luz",
    "tono pin 8 frecuencia 1000 duracion 200",
    "silencio pin 8",
]

REFERENCIA_LENGUAJE = """
Integrated — Lenguaje en español
================================

ESTRUCTURA
  al iniciar / repetir siempre / si / si no / fin si
  repetir N veces / mientras / fin mientras / romper / continuar
  funcion nombre / fin funcion / llamar nombre
  Las funciones reutilizables no reciben parametros y deben definirse antes de usarse.
  Ejemplo:
    funcion encenderLuz
      hacer que pin 13, encendido
    fin funcion
    al iniciar
    llamar encenderLuz

VARIABLES Y SERIAL
  variable entero|decimal|texto|verdadero o falso = nombre
  asignar nombre = valor
  sumar cantidad a variable / restar cantidad a variable
  incrementar variable / decrementar variable
  limitar variable entre minimo y maximo
  aleatorio entre minimo y maximo en variable
  velocidad serie 115200
  escribe mensaje | escribe texto, variable

PINES
  configurar pin N, salida|entrada|entrada con resistencia
  hacer que pin N, encendido|apagado
  leer pin digital N en var
  leer pin analógico A0 en var
  escribir pwm pin N con valor
  configurar led integrado
  encender led integrado | apagar led integrado
  parpadear led integrado 500

PROYECTOS REALES
  Ultrasonido HC-SR04:
    configurar ultrasonido trig 12 echo 13
    medir distancia en distancia

  Servo:
    configurar servo pin 9
    girar servo a 90

  Motores (L298N / similar):
    configurar motor izquierdo pwm 5 in1 6 in2 7
    motor izquierdo adelante 200
    motor derecho atras 150
    parar motores

  Invernadero / riego:
    leer humedad suelo A0 en humedad
    leer temperatura lm35 A1 en temperatura

  Luz / alarma:
    leer luz A0 en luz
    tono pin 8 frecuencia 1000 duracion 200
    silencio pin 8

Archivos del proyecto: extensión .int_esp

RED (ESP32 / ESP8266)
  wifi conectar "nombre" "clave"
  wifi nombre "MiRed"
  wifi clave "contraseña"
  wifi password "contraseña"
  wifi conectar nombre password
  wifi iniciar
  wifi crear punto de acceso "MiDispositivo" "clave1234"
  El punto de acceso crea una red propia; luego conecta el telefono o PC a ella.
  wifi ip en direccion
  wifi mostrar ip
  wifi desconectar
  servidor iniciar 80
  servidor ruta "/" "Hola desde la placa"
  servidor html "/" "<h1>Hola mundo</h1>"
  servidor html "/":
    <html>
      <head><style>body { color: green; }</style></head>
      <body><h1>Hola mundo</h1><script>console.log('ok');</script></body>
    </html>
  fin html
  contenido html "/":
    <html><body><h1>Contenido HTML delimitado</h1></body></html>
  fin contenido html
  servidor pagina "/" "index.html"
  servidor atender
  Estos comandos requieren una placa ESP32 o ESP8266; no son compatibles con Arduino AVR.

GUIA RAPIDA DE PROBLEMAS
  WiFi STA (conectarse a un router):
    Usa wifi conectar "NOMBRE_REAL" "CLAVE_REAL".
    La red debe ser visible y normalmente de 2.4 GHz para ESP32.
    Abre Monitor serie a 115200: muestra la IP si conecta.
    Estado 6 significa que no se encontro el SSID.

  WiFi AP (crear una red desde el ESP32):
    Usa wifi crear punto de acceso "MiRed" "12345678".
    Conecta el telefono o PC a MiRed y abre http://192.168.4.1.
    La clave debe tener al menos 8 caracteres.

  Paginas web:
    Para HTML corto usa servidor html "/" "<h1>Hola</h1>".
    Para HTML, CSS y JavaScript largos crea una carpeta web/ con index.html,
    estilos.css, app.js e imagenes. La aplicacion la detecta al cargar.
    Usa servidor pagina "/" "index.html" y servidor atender.

  Placa no responde:
    Confirma la placa y el puerto COM, cierra el Monitor serie antes de cargar,
    revisa la consola y pulsa reset en la placa si el bootloader lo necesita.
    Arduino AVR no tiene WiFi integrado; usa ESP32 o ESP8266 para red.

  Carga lenta o detenida:
    La compilacion ocurre automaticamente al pulsar Cargar a la placa.
    La subida tiene timeout y la consola muestra la fase del proceso.

  Orden recomendado:
    1. Seleccionar placa.
    2. Seleccionar o esperar el puerto COM.
    3. Traducir (F5) y revisar el C++.
    4. Cargar a la placa.
    5. Abrir Monitor serie para ver IP y diagnosticos.
"""
