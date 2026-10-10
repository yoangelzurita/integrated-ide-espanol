"""Proyectos de ejemplo listos para abrir en Integrated (.int_esp).

Ejemplos comunes, prácticos y actualizados con nuevas funciones,
incluyendo control web desde el celular con ESP32 S2 Mini.
"""

EJEMPLOS = {
    "Básico — Hola por Monitor Serie": '''// Abre el Monitor Serie para ver los mensajes.
velocidad serie 115200

al iniciar
escribe Hola, Integrated esta funcionando

repetir siempre
escribe El programa sigue activo
esperar 2000
''',

    "Básico — Semáforo de tres luces": '''// LED verde en pin 10, amarillo en 11 y rojo en 12.
// Usa una resistencia en serie con cada LED.
velocidad serie 115200

al iniciar
configurar pin 10, salida
configurar pin 11, salida
configurar pin 12, salida

repetir siempre
hacer que pin 10, encendido
hacer que pin 11, apagado
hacer que pin 12, apagado
esperar 3000
hacer que pin 10, apagado
hacer que pin 11, encendido
esperar 1000
hacer que pin 11, apagado
hacer que pin 12, encendido
esperar 3000
''',

    "Básico — Sensor de luz y aviso": '''// LDR con resistencia como divisor de voltaje a A0.
// LED en el pin 13: enciende cuando el nivel de luz baja del umbral.
variable entero nivel
velocidad serie 115200

al iniciar
configurar pin 13, salida

repetir siempre
leer pin analógico A0 en nivel
escribe Nivel de luz , nivel
si nivel es menor a 500
  hacer que pin 13, encendido
si no
  hacer que pin 13, apagado
fin si
esperar 500
''',

    "ESP32 S2 Mini — Hotspot y Página Personalizable": '''// ESP32 S2 Mini crea su propia red y aloja esta página web.
// Conecta el celular a ESP32_Panel (clave: 12345678) y abre http://192.168.4.1
// Cambia el título, los colores y textos editando el HTML y CSS de abajo.
velocidad serie 115200

al iniciar
configurar pin 15, salida
hacer que pin 15, apagado
wifi crear punto de acceso "ESP32_Panel" "12345678"
servidor iniciar 80
servidor al recibir "/encender" encender pin 15 y redirigir "/"
servidor al recibir "/apagar" apagar pin 15 y redirigir "/"
servidor al recibir "/alternar" alternar pin 15 y redirigir "/"

contenido html "/":
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mi casa inteligente</title>
  <style>
    body { background: #eef2ff; color: #172554; font-family: Arial, sans-serif; text-align: center; padding: 24px; }
    main { background: white; border-radius: 18px; padding: 24px; max-width: 380px; margin: auto; }
    h1 { color: #4338ca; }
    a { display: block; padding: 14px; margin: 12px 0; border-radius: 10px; color: white; text-decoration: none; font-weight: bold; }
    .on { background: #16a34a; }
    .off { background: #dc2626; }
    .toggle { background: #4f46e5; }
  </style>
</head>
<body>
  <main>
    <h1>Mi casa inteligente</h1>
    <p>Controla la luz conectada al GPIO 15.</p>
    <a class="on" href="/encender">Encender luz</a>
    <a class="off" href="/apagar">Apagar luz</a>
    <a class="toggle" href="/alternar">Cambiar estado</a>
  </main>
</body>
</html>
fin contenido html

repetir siempre
servidor atender
''',

    "Funciones Reutilizables — Control de Luz": '''// Define acciones una sola vez y vuelve a usarlas con "llamar".
// Boton entre pin 2 y GND; LED o modulo de rele conectado al pin 13.
velocidad serie 9600

funcion encenderLuz
  hacer que pin 13, encendido
fin funcion

funcion apagarLuz
  hacer que pin 13, apagado
fin funcion

al iniciar
configurar pin 2, entrada con resistencia
configurar pin 13, salida
llamar apagarLuz

repetir siempre
si pin 2 esta en bajo
  llamar encenderLuz
  esperar 250
  llamar apagarLuz
  esperar 250
fin si
''',

    "Riego Automático de Maceta": '''// Sensor de humedad en A0; modulo de rele/bomba en pin 8.
// Calibra el umbral comparando lecturas de tierra seca y humeda.
// ESP32 suele leer 0-4095; para Arduino Uno reemplaza el umbral por uno calibrado
// en su rango (0-1023). No conectes la bomba directamente a un GPIO.
variable entero humedad
velocidad serie 9600

al iniciar
configurar pin 8, salida
hacer que pin 8, apagado
escribe Riego automatico listo

repetir siempre
leer pin analógico A0 en humedad
escribe Lectura del sensor , humedad
si humedad es mayor a 2500
  hacer que pin 8, encendido
  escribe Suelo seco: bomba encendida
si no
  hacer que pin 8, apagado
  escribe Suelo humedo: bomba apagada
fin si
esperar 1000
''',

    "Control de Relé con Pulsador (Toggle)": '''// Control de luz o electrodoméstico con un pulsador
// Al presionar el botón una vez enciende; al presionar de nuevo apaga.
// Botón en pin 2 (con resistencia interna pullup), Relé o LED en pin 13
velocidad serie 115200

al iniciar
configurar pin 2, entrada con resistencia
configurar pin 13, salida
hacer que pin 13, apagado
escribe Sistema de control con pulsador listo

repetir siempre
// Si el botón está presionado (conecta a GND al pulsar)
si pin 2 esta en bajo
  alternar pin 13
  escribe Estado de relé cambiado
  esperar 250
fin si
esperar 50
''',

    "Alarma de Seguridad (Presencia y Buzzer)": '''// Alarma antirrobo: Sensor de ultrasonido en pines 12 (trig) y 13 (echo)
// Buzzer en pin 4, LED de advertencia en pin 5
variable decimal distancia
velocidad serie 115200

al iniciar
configurar pin 5, salida
configurar ultrasonido trig 12 echo 13
hacer que pin 5, apagado
escribe Alarma de seguridad activada

repetir siempre
medir distancia en distancia
escribe Distancia en cm , distancia

// Si alguien se acerca a menos de 30 centímetros
si distancia es menor a 30
  hacer que pin 5, encendido
  tono pin 4 frecuencia 1000 duracion 150
  esperar 150
  tono pin 4 frecuencia 800 duracion 150
  esperar 150
si no
  hacer que pin 5, apagado
  silencio pin 4
fin si

esperar 100
''',

    "Termostato con Ventilador Automático": '''// Control de temperatura con LM35 en pin analógico A0
// Ventilador / Cooler en pin digital 8
variable decimal temp
velocidad serie 115200

al iniciar
configurar pin 8, salida
hacer que pin 8, apagado
escribe Termostato inteligente iniciado

repetir siempre
leer temperatura lm35 A0 en temp
escribe Temperatura actual C , temp

// Si la temperatura sube de 28 grados, enciende ventilador
si temp es mayor a 28
  hacer que pin 8, encendido
  escribe Ventilador: ENCENDIDO
si no
  hacer que pin 8, apagado
  escribe Ventilador: APAGADO
fin si

esperar 2000
''',

    "Regulador de Brillo con Potenciómetro (PWM)": '''// Dimmer de luz: Lee potenciómetro en A0 y gradúa el brillo de un LED
// Potenciómetro en A0, LED en pin PWM 9 (o pin 15 en ESP32)
variable entero lectura
variable entero brillo
velocidad serie 115200

al iniciar
configurar pin 9, salida
escribe Regulador PWM listo

repetir siempre
leer pin analógico A0 en lectura
mapear lectura de 0 a 1023 hacia 0 a 255 en brillo
escribir pwm pin 9 con brillo
escribe Brillo ajustado a , brillo
esperar 30
''',

    "Semáforo Inteligente con Paso Peatonal": '''// Semáforo con pulsador peatonal
// Luces: Verde (pin 10), Amarillo (pin 11), Rojo (pin 12)
// Botón de peatón: pin 2 con resistencia
velocidad serie 115200

al iniciar
configurar pin 10, salida
configurar pin 11, salida
configurar pin 12, salida
configurar pin 2, entrada con resistencia
hacer que pin 10, encendido
hacer que pin 11, apagado
hacer que pin 12, apagado

repetir siempre
// Si el peatón pulsa el botón, cambia a amarillo y luego rojo
si pin 2 esta en bajo
  escribe Peaton esperando cruce
  esperar 1000
  // Cambiar a amarillo
  hacer que pin 10, apagado
  hacer que pin 11, encendido
  esperar 2000
  // Cambiar a rojo (peatón cruza)
  hacer que pin 11, apagado
  hacer que pin 12, encendido
  esperar 5000
  // Volver a verde
  hacer que pin 12, apagado
  hacer que pin 10, encendido
fin si
esperar 100
''',

    "Parpadeo LED Simple": '''// Parpadeo básico de LED en pin 13 (o pin 15 para ESP32 S2 Mini)
velocidad serie 115200

al iniciar
configurar pin 13, salida

repetir siempre
hacer que pin 13, encendido
esperar 500
hacer que pin 13, apagado
esperar 500
''',
}


def nombres_ejemplos():
    return list(EJEMPLOS.keys())


def codigo_ejemplo(nombre: str) -> str:
    return EJEMPLOS.get(nombre, "")
