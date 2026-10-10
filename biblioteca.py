"""Biblioteca completa de comandos del lenguaje Integrated (espanol -> C++/Arduino)."""

from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
# Estructura de cada comando:
#   nombre      : str  - Nombre visible en la UI
#   categoria   : str  - Grupo al que pertenece
#   sintaxis    : str  - Sintaxis exacta del comando
#   descripcion : str  - Que hace el comando
#   ejemplo     : str  - Ejemplo de uso en .int_esp
#   cpp         : str  - Codigo C++ equivalente generado
#   notas       : str | None  - Observaciones adicionales
#   placas      : str  - Compatibilidad de placa
# ─────────────────────────────────────────────────────────────────────────────

CATEGORIAS_ORDEN = [
    "Estructura",
    "Funciones",
    "Variables",
    "Serial / Monitor",
    "Pines digitales",
    "Pines analogicos",
    "Temporizacion",
    "Condicionales",
    "Bucles",
    "Matematicas",
    "LED integrado",
    "Servo",
    "Ultrasonido",
    "Motores",
    "Buzzer / Tono",
    "Sensores",
    "WiFi (ESP32/ESP8266)",
    "Servidor Web (ESP32/ESP8266)",
]

COMANDOS: list[dict] = [

    # ── ESTRUCTURA ────────────────────────────────────────────────────────────
    {
        "nombre": "al iniciar",
        "categoria": "Estructura",
        "sintaxis": "al iniciar",
        "descripcion": (
            "Marca el inicio del bloque de configuracion. Todo lo que escribas debajo "
            "de esta linea se ejecuta una sola vez cuando la placa enciende o se reinicia. "
            "Es equivalente a la funcion setup() de Arduino."
        ),
        "ejemplo": (
            "al iniciar\n"
            "configurar pin 13, salida\n"
            "escribe Placa iniciada"
        ),
        "cpp": (
            "void setup() {\n"
            "  Serial.begin(115200);\n"
            "  pinMode(13, OUTPUT);\n"
            "  Serial.println(\"Placa iniciada\");\n"
            "}"
        ),
        "notas": "Obligatorio si vas a configurar pines o hardware. Solo puede aparecer una vez.",
        "placas": "Todas",
    },
    {
        "nombre": "repetir siempre",
        "categoria": "Estructura",
        "sintaxis": "repetir siempre",
        "descripcion": (
            "Marca el inicio del bloque principal que se repite sin fin. "
            "Es equivalente al loop() de Arduino. Aqui va la logica principal del programa."
        ),
        "ejemplo": (
            "repetir siempre\n"
            "hacer que pin 13, encendido\n"
            "esperar 500\n"
            "hacer que pin 13, apagado\n"
            "esperar 500"
        ),
        "cpp": (
            "void loop() {\n"
            "  digitalWrite(13, HIGH);\n"
            "  delay(500);\n"
            "  digitalWrite(13, LOW);\n"
            "  delay(500);\n"
            "}"
        ),
        "notas": "Obligatorio en la mayoria de proyectos. Solo puede aparecer una vez.",
        "placas": "Todas",
    },
    {
        "nombre": "funcion",
        "categoria": "Funciones",
        "sintaxis": "funcion nombre\n  instrucciones\nfin funcion",
        "descripcion": (
            "Crea un bloque reutilizable sin parametros. Define la funcion antes de "
            "usarla y llama su nombre desde al iniciar o repetir siempre."
        ),
        "ejemplo": (
            "funcion encenderLuz\n"
            "  hacer que pin 13, encendido\n"
            "fin funcion\n\n"
            "al iniciar\n"
            "llamar encenderLuz"
        ),
        "cpp": "void encenderLuz() {\n  digitalWrite(13, HIGH);\n}",
        "notas": "Por ahora las funciones no reciben parametros ni devuelven valores.",
        "placas": "Todas",
    },
    {
        "nombre": "llamar funcion",
        "categoria": "Funciones",
        "sintaxis": "llamar nombre",
        "descripcion": "Ejecuta una funcion definida previamente en el proyecto.",
        "ejemplo": "llamar encenderLuz",
        "cpp": "encenderLuz();",
        "notas": "El nombre debe coincidir exactamente con el declarado en funcion.",
        "placas": "Todas",
    },
    {
        "nombre": "velocidad serie",
        "categoria": "Estructura",
        "sintaxis": "velocidad serie 115200",
        "descripcion": (
            "Define la velocidad de comunicacion del puerto serie (baud rate). "
            "Debe coincidir con la velocidad del Monitor serie. "
            "Valores comunes: 9600, 57600, 115200."
        ),
        "ejemplo": "velocidad serie 115200",
        "cpp": "Serial.begin(115200);",
        "notas": "Por defecto se usa 115200. Cambiar solo si tienes una razon especifica.",
        "placas": "Todas",
    },

    # ── VARIABLES ─────────────────────────────────────────────────────────────
    {
        "nombre": "variable entero",
        "categoria": "Variables",
        "sintaxis": "variable entero = nombre",
        "descripcion": (
            "Declara una variable global de tipo entero (numero sin decimales). "
            "Se inicializa en 0 y puede usarse en cualquier seccion del codigo."
        ),
        "ejemplo": (
            "variable entero = contador\n\n"
            "repetir siempre\n"
            "asignar contador = contador + 1\n"
            "escribe Cuenta , contador\n"
            "esperar 500"
        ),
        "cpp": "int contador = 0;",
        "notas": "Rango: -2147483648 a 2147483647 en ESP32, -32768 a 32767 en Arduino AVR.",
        "placas": "Todas",
    },
    {
        "nombre": "variable decimal",
        "categoria": "Variables",
        "sintaxis": "variable decimal = nombre",
        "descripcion": (
            "Declara una variable global de tipo decimal (numero con coma flotante). "
            "Se inicializa en 0.0. Ideal para temperaturas, distancias, voltajes, etc."
        ),
        "ejemplo": (
            "variable decimal = temperatura\n\n"
            "repetir siempre\n"
            "leer temperatura lm35 A1 en temperatura\n"
            "escribe Temp C , temperatura\n"
            "esperar 2000"
        ),
        "cpp": "float temperatura = 0.0;",
        "notas": "Usa punto (.) como separador decimal en operaciones matematicas.",
        "placas": "Todas",
    },
    {
        "nombre": "variable texto",
        "categoria": "Variables",
        "sintaxis": "variable texto = nombre",
        "descripcion": (
            "Declara una variable global de tipo texto (cadena de caracteres String). "
            "Se inicializa como cadena vacia. Util para IP, nombres, mensajes, etc."
        ),
        "ejemplo": (
            "variable texto = mensaje\n\n"
            "al iniciar\n"
            "asignar mensaje = \"Hola mundo\"\n"
            "escribe mensaje"
        ),
        "cpp": 'String mensaje = "";',
        "notas": 'Escribe textos entre comillas dobles: "Mi texto".',
        "placas": "Todas",
    },
    {
        "nombre": "variable verdadero o falso",
        "categoria": "Variables",
        "sintaxis": "variable verdadero o falso = nombre",
        "descripcion": (
            "Declara una variable booleana. Solo puede tener dos valores: "
            "verdadero (1/true) o falso (0/false). Ideal para banderas y estados."
        ),
        "ejemplo": (
            "variable verdadero o falso = encendido\n\n"
            "al iniciar\n"
            "asignar encendido = 1"
        ),
        "cpp": "bool encendido = false;",
        "notas": "Usa 1 o true para verdadero, 0 o false para falso.",
        "placas": "Todas",
    },
    {
        "nombre": "asignar",
        "categoria": "Variables",
        "sintaxis": "asignar nombre = valor",
        "descripcion": (
            "Asigna un nuevo valor a una variable ya declarada. "
            "El valor puede ser un numero, texto, expresion matematica u otra variable."
        ),
        "ejemplo": (
            "variable entero = x\n\n"
            "repetir siempre\n"
            "asignar x = x + 1\n"
            "escribe x , x\n"
            "esperar 500"
        ),
        "cpp": "x = x + 1;",
        "notas": "Se puede usar dentro de 'al iniciar' y 'repetir siempre'.",
        "placas": "Todas",
    },

    # ── SERIAL / MONITOR ──────────────────────────────────────────────────────
    {
        "nombre": "escribe",
        "categoria": "Serial / Monitor",
        "sintaxis": "escribe mensaje\nescribe texto, variable",
        "descripcion": (
            "Envia texto al Monitor serie con salto de linea al final. "
            "Con la coma puedes combinar un texto fijo con el valor de una variable."
        ),
        "ejemplo": (
            "variable entero = luz\n\n"
            "repetir siempre\n"
            "leer pin analogico A0 en luz\n"
            "escribe Nivel de luz , luz\n"
            "esperar 500"
        ),
        "cpp": (
            'Serial.print("Nivel de luz ");\n'
            "Serial.println(luz);"
        ),
        "notas": "Abre el Monitor serie (Ctrl+Shift+M) a 115200 baud para ver la salida.",
        "placas": "Todas",
    },
    {
        "nombre": "escribir sin salto",
        "categoria": "Serial / Monitor",
        "sintaxis": "escribir sin salto mensaje",
        "descripcion": (
            "Envia texto al Monitor serie SIN salto de linea al final. "
            "Util para construir mensajes en partes en la misma linea."
        ),
        "ejemplo": (
            "repetir siempre\n"
            "escribir sin salto Valor: \n"
            "escribe , analogRead(A0)"
        ),
        "cpp": 'Serial.print("Valor: ");',
        "notas": None,
        "placas": "Todas",
    },
    {
        "nombre": "leer (serial)",
        "categoria": "Serial / Monitor",
        "sintaxis": "leer nombre_variable",
        "descripcion": (
            "Espera a que el usuario escriba algo en el Monitor serie y lo guarda "
            "en la variable indicada. Convierte automaticamente segun el tipo declarado."
        ),
        "ejemplo": (
            "variable entero = velocidad\n\n"
            "al iniciar\n"
            "escribe Escribe la velocidad:\n"
            "leer velocidad\n"
            "escribe Velocidad recibida , velocidad"
        ),
        "cpp": (
            "while (Serial.available() == 0) { delay(10); }\n"
            "velocidad = Serial.readStringUntil('\\n').toInt();"
        ),
        "notas": "El programa se detiene hasta recibir datos. Solo para variables ya declaradas.",
        "placas": "Todas",
    },

    # ── PINES DIGITALES ───────────────────────────────────────────────────────
    {
        "nombre": "configurar pin",
        "categoria": "Pines digitales",
        "sintaxis": (
            "configurar pin N, salida\n"
            "configurar pin N, entrada\n"
            "configurar pin N, entrada con resistencia"
        ),
        "descripcion": (
            "Configura el modo de un pin digital.\n"
            "  salida: para controlar LEDs, reles, motores, etc.\n"
            "  entrada: para leer sensores o botones (sin resistencia interna).\n"
            "  entrada con resistencia: activa pull-up interno (recomendado para botones)."
        ),
        "ejemplo": (
            "al iniciar\n"
            "configurar pin 13, salida\n"
            "configurar pin 2, entrada con resistencia"
        ),
        "cpp": (
            "pinMode(13, OUTPUT);\n"
            "pinMode(2, INPUT_PULLUP);"
        ),
        "notas": "Configura los pines siempre en 'al iniciar' antes de usarlos.",
        "placas": "Todas",
    },
    {
        "nombre": "hacer que pin",
        "categoria": "Pines digitales",
        "sintaxis": (
            "hacer que pin N, encendido\n"
            "hacer que pin N, apagado"
        ),
        "descripcion": (
            "Pone un pin de salida en estado ALTO (encendido, 3.3V/5V) "
            "o BAJO (apagado, 0V). Equivalente a digitalWrite() de Arduino."
        ),
        "ejemplo": (
            "repetir siempre\n"
            "hacer que pin 13, encendido\n"
            "esperar 1000\n"
            "hacer que pin 13, apagado\n"
            "esperar 1000"
        ),
        "cpp": (
            "digitalWrite(13, HIGH);\n"
            "delay(1000);\n"
            "digitalWrite(13, LOW);\n"
            "delay(1000);"
        ),
        "notas": "El pin debe estar configurado como salida. Tambien acepta 'alto'/'bajo'.",
        "placas": "Todas",
    },
    {
        "nombre": "leer pin digital",
        "categoria": "Pines digitales",
        "sintaxis": "leer pin digital N en variable",
        "descripcion": (
            "Lee el estado de un pin digital (0 = bajo, 1 = alto) y guarda el resultado "
            "en la variable indicada. Util para botones, sensores IR, finales de carrera."
        ),
        "ejemplo": (
            "variable entero = boton\n\n"
            "al iniciar\n"
            "configurar pin 2, entrada con resistencia\n\n"
            "repetir siempre\n"
            "leer pin digital 2 en boton\n"
            "si boton es igual a 0\n"
            "escribe Boton presionado\n"
            "fin si\n"
            "esperar 50"
        ),
        "cpp": (
            "boton = digitalRead(2);\n"
            "if (boton == 0) {\n"
            '  Serial.println("Boton presionado");\n'
            "}"
        ),
        "notas": "Con pull-up interno: 0 = pulsado, 1 = suelto.",
        "placas": "Todas",
    },

    {
        "nombre": "alternar pin",
        "categoria": "Pines digitales",
        "sintaxis": "alternar pin N",
        "descripcion": (
            "Cambia el estado de un pin: si estaba encendido lo apaga, y si estaba apagado "
            "lo enciende (efecto conmutador / toggle). Ideal para controlar luces o relés con un pulsador."
        ),
        "ejemplo": (
            "repetir siempre\n"
            "si pin 2 esta en bajo\n"
            "  alternar pin 13\n"
            "  esperar 250\n"
            "fin si"
        ),
        "cpp": "digitalWrite(13, !digitalRead(13));",
        "notas": "Requiere que el pin haya sido configurado como salida.",
        "placas": "Todas",
    },

    # ── PINES ANALOGICOS ──────────────────────────────────────────────────────
    {
        "nombre": "leer pin analogico",
        "categoria": "Pines analogicos",
        "sintaxis": "leer pin analogico A0 en variable",
        "descripcion": (
            "Lee el valor del convertidor ADC en el pin indicado. "
            "Rango: 0-1023 (Arduino, 10 bits) o 0-4095 (ESP32, 12 bits). "
            "Admite notacion Ax (A0, A1...) o numero de GPIO."
        ),
        "ejemplo": (
            "variable entero = valor\n\n"
            "repetir siempre\n"
            "leer pin analogico A0 en valor\n"
            "escribe Valor ADC , valor\n"
            "esperar 200"
        ),
        "cpp": "valor = analogRead(A0);",
        "notas": "No configures el pin como salida antes de leerlo analógicamente.",
        "placas": "Todas",
    },
    {
        "nombre": "escribir pwm",
        "categoria": "Pines analogicos",
        "sintaxis": "escribir pwm pin N con valor",
        "descripcion": (
            "Escribe una senal PWM en un pin. El valor va de 0 (apagado) a 255 (maximo). "
            "Sirve para controlar brillo de LEDs, velocidad de motores DC, etc."
        ),
        "ejemplo": (
            "variable entero = brillo\n\n"
            "repetir siempre\n"
            "asignar brillo = brillo + 5\n"
            "limitar brillo entre 0 y 255\n"
            "escribir pwm pin 9 con brillo\n"
            "esperar 20"
        ),
        "cpp": "analogWrite(9, brillo);",
        "notas": "Solo en pines PWM (con ~ en Arduino). En ESP32 todos los GPIO soportan PWM.",
        "placas": "Todas",
    },

    # ── TEMPORIZACION ─────────────────────────────────────────────────────────
    {
        "nombre": "esperar",
        "categoria": "Temporizacion",
        "sintaxis": "esperar N",
        "descripcion": (
            "Pausa la ejecucion del programa durante N milisegundos "
            "(1 segundo = 1000 ms). Durante la espera el microcontrolador no hace nada mas."
        ),
        "ejemplo": (
            "repetir siempre\n"
            "hacer que pin 13, encendido\n"
            "esperar 500\n"
            "hacer que pin 13, apagado\n"
            "esperar 500"
        ),
        "cpp": "delay(500);",
        "notas": "Para ESP32/ESP8266 en modo WiFi, el traductor agrega yield() automaticamente.",
        "placas": "Todas",
    },
    {
        "nombre": "esperar microsegundos",
        "categoria": "Temporizacion",
        "sintaxis": "esperar microsegundos N",
        "descripcion": (
            "Pausa la ejecucion durante N microsegundos (1 ms = 1000 us). "
            "Ideal para pulsos precisos como el sensor ultrasonido HC-SR04."
        ),
        "ejemplo": (
            "repetir siempre\n"
            "hacer que pin 12, encendido\n"
            "esperar microsegundos 10\n"
            "hacer que pin 12, apagado"
        ),
        "cpp": (
            "digitalWrite(12, HIGH);\n"
            "delayMicroseconds(10);\n"
            "digitalWrite(12, LOW);"
        ),
        "notas": "Para tiempos muy cortos (<= 100 us) es mas preciso que esperar.",
        "placas": "Todas",
    },

    # ── CONDICIONALES ─────────────────────────────────────────────────────────
    {
        "nombre": "si / si no / fin si",
        "categoria": "Condicionales",
        "sintaxis": (
            "si condicion\n"
            "  (bloque verdadero)\n"
            "si no\n"
            "  (bloque falso)\n"
            "fin si"
        ),
        "descripcion": (
            "Ejecuta codigo solo si se cumple una condicion. "
            "Con 'si no' se maneja el caso contrario.\n\n"
            "Operadores disponibles:\n"
            "  es igual a        ->  ==\n"
            "  es diferente a    ->  !=\n"
            "  es mayor a        ->  >\n"
            "  es menor a        ->  <\n"
            "  es mayor o igual a -> >=\n"
            "  es menor o igual a -> <=\n"
            "  y                 ->  &&\n"
            "  o                 ->  ||\n"
            "  no                ->  !"
        ),
        "ejemplo": (
            "variable entero = luz\n\n"
            "repetir siempre\n"
            "leer pin analogico A0 en luz\n"
            "si luz es menor a 300\n"
            "hacer que pin 13, encendido\n"
            "si no\n"
            "hacer que pin 13, apagado\n"
            "fin si\n"
            "esperar 100"
        ),
        "cpp": (
            "if (luz < 300) {\n"
            "  digitalWrite(13, HIGH);\n"
            "} else {\n"
            "  digitalWrite(13, LOW);\n"
            "}"
        ),
        "notas": "Puedes anidar varios 'si' dentro de otros. Cada uno necesita su 'fin si'.",
        "placas": "Todas",
    },

    # ── BUCLES ────────────────────────────────────────────────────────────────
    {
        "nombre": "repetir N veces",
        "categoria": "Bucles",
        "sintaxis": "repetir N veces\n  (bloque)\nfin repetir",
        "descripcion": (
            "Repite el bloque de codigo exactamente N veces. "
            "Equivale a un bucle for en C++."
        ),
        "ejemplo": (
            "repetir siempre\n"
            "repetir 5 veces\n"
            "tono pin 8 frecuencia 1000 duracion 100\n"
            "esperar 150\n"
            "fin repetir\n"
            "esperar 2000"
        ),
        "cpp": (
            "for (int __i = 0; __i < 5; __i++) {\n"
            "  tone(8, 1000, 100);\n"
            "  delay(150);\n"
            "}"
        ),
        "notas": "Cierra siempre con 'fin repetir'.",
        "placas": "Todas",
    },
    {
        "nombre": "mientras",
        "categoria": "Bucles",
        "sintaxis": "mientras condicion\n  (bloque)\nfin mientras",
        "descripcion": (
            "Repite el bloque mientras la condicion sea verdadera. "
            "La condicion se evalua antes de cada iteracion."
        ),
        "ejemplo": (
            "variable entero = angulo\n\n"
            "repetir siempre\n"
            "asignar angulo = 0\n"
            "mientras angulo es menor a 181\n"
            "girar servo a angulo\n"
            "asignar angulo = angulo + 1\n"
            "esperar 15\n"
            "fin mientras"
        ),
        "cpp": (
            "while (angulo < 181) {\n"
            "  __servoIntegrated.write(angulo);\n"
            "  angulo = angulo + 1;\n"
            "  delay(15);\n"
            "}"
        ),
        "notas": "Usa 'romper' para salir antes de tiempo. Cierra con 'fin mientras'.",
        "placas": "Todas",
    },
    {
        "nombre": "romper",
        "categoria": "Bucles",
        "sintaxis": "romper",
        "descripcion": "Sale inmediatamente del bucle actual (mientras o repetir N veces).",
        "ejemplo": (
            "variable entero = x\n\n"
            "repetir siempre\n"
            "asignar x = x + 1\n"
            "si x es mayor a 100\n"
            "romper\n"
            "fin si"
        ),
        "cpp": "break;",
        "notas": None,
        "placas": "Todas",
    },
    {
        "nombre": "continuar",
        "categoria": "Bucles",
        "sintaxis": "continuar",
        "descripcion": "Salta al inicio de la siguiente iteracion del bucle actual.",
        "ejemplo": (
            "repetir 10 veces\n"
            "si x es diferente a 5\n"
            "continuar\n"
            "fin si\n"
            "escribe Exactamente 5"
        ),
        "cpp": "continue;",
        "notas": None,
        "placas": "Todas",
    },

    # ── MATEMATICAS ───────────────────────────────────────────────────────────
    {
        "nombre": "mapear",
        "categoria": "Matematicas",
        "sintaxis": "mapear var de minOrig a maxOrig hacia minDest a maxDest en resultado",
        "descripcion": (
            "Convierte un valor de un rango a otro rango proporcionalmente. "
            "Ejemplo: convierte 0-1023 (ADC) a 0-255 (PWM)."
        ),
        "ejemplo": (
            "variable entero = adc\n"
            "variable entero = brillo\n\n"
            "repetir siempre\n"
            "leer pin analogico A0 en adc\n"
            "mapear adc de 0 a 1023 hacia 0 a 255 en brillo\n"
            "escribir pwm pin 9 con brillo\n"
            "esperar 10"
        ),
        "cpp": "brillo = map(adc, 0, 1023, 0, 255);",
        "notas": "El resultado puede salir del rango destino si la entrada sale del rango origen.",
        "placas": "Todas",
    },
    {
        "nombre": "limitar",
        "categoria": "Matematicas",
        "sintaxis": "limitar variable entre min y max",
        "descripcion": (
            "Mantiene una variable dentro de un rango dado. "
            "Si es menor que min, la pone en min. Si es mayor que max, la pone en max."
        ),
        "ejemplo": (
            "variable entero = velocidad\n\n"
            "repetir siempre\n"
            "asignar velocidad = velocidad + 10\n"
            "limitar velocidad entre 0 y 255\n"
            "escribir pwm pin 9 con velocidad\n"
            "esperar 100"
        ),
        "cpp": "velocidad = constrain(velocidad, 0, 255);",
        "notas": None,
        "placas": "Todas",
    },
    {
        "nombre": "aleatorio",
        "categoria": "Matematicas",
        "sintaxis": "aleatorio entre min y max en variable",
        "descripcion": (
            "Genera un numero aleatorio entre min y max (ambos inclusive) "
            "y lo guarda en la variable indicada."
        ),
        "ejemplo": (
            "variable entero = dado\n\n"
            "repetir siempre\n"
            "aleatorio entre 1 y 6 en dado\n"
            "escribe Resultado dado , dado\n"
            "esperar 1000"
        ),
        "cpp": "dado = random(1, 6 + 1);",
        "notas": "El generador no es criptograficamente seguro. No apto para seguridad.",
        "placas": "Todas",
    },

    # ── LED INTEGRADO ─────────────────────────────────────────────────────────
    {
        "nombre": "configurar led integrado",
        "categoria": "LED integrado",
        "sintaxis": "configurar led integrado",
        "descripcion": (
            "Configura el LED integrado de la placa como salida. "
            "En Arduino UNO es el pin 13. En ESP32 S2 Mini es el GPIO 15 (LED azul)."
        ),
        "ejemplo": (
            "al iniciar\n"
            "configurar led integrado"
        ),
        "cpp": "pinMode(LED_BUILTIN, OUTPUT);",
        "notas": "Llama a esto en 'al iniciar' antes de usar el LED integrado.",
        "placas": "Todas",
    },
    {
        "nombre": "encender / apagar led integrado",
        "categoria": "LED integrado",
        "sintaxis": (
            "encender led integrado\n"
            "apagar led integrado"
        ),
        "descripcion": "Enciende o apaga el LED integrado de la placa.",
        "ejemplo": (
            "al iniciar\n"
            "configurar led integrado\n\n"
            "repetir siempre\n"
            "encender led integrado\n"
            "esperar 200\n"
            "apagar led integrado\n"
            "esperar 800"
        ),
        "cpp": (
            "digitalWrite(LED_BUILTIN, HIGH);\n"
            "delay(200);\n"
            "digitalWrite(LED_BUILTIN, LOW);\n"
            "delay(800);"
        ),
        "notas": None,
        "placas": "Todas",
    },
    {
        "nombre": "parpadear led integrado",
        "categoria": "LED integrado",
        "sintaxis": "parpadear led integrado N",
        "descripcion": (
            "Hace parpadear el LED integrado con el intervalo N en milisegundos. "
            "Lo enciende N ms y lo apaga N ms. Util para indicar actividad."
        ),
        "ejemplo": (
            "al iniciar\n"
            "configurar led integrado\n\n"
            "repetir siempre\n"
            "parpadear led integrado 500\n"
            "servidor atender"
        ),
        "cpp": (
            "digitalWrite(LED_BUILTIN, HIGH);\n"
            "delay(500);\n"
            "yield();\n"
            "digitalWrite(LED_BUILTIN, LOW);\n"
            "delay(500);\n"
            "yield();"
        ),
        "notas": "Muy util para indicar que el ESP esta activo mientras atiende el servidor.",
        "placas": "Todas",
    },

    # ── SERVO ─────────────────────────────────────────────────────────────────
    {
        "nombre": "configurar servo",
        "categoria": "Servo",
        "sintaxis": "configurar servo pin N",
        "descripcion": (
            "Conecta y configura un servomotor en el pin indicado. "
            "Carga automaticamente la libreria Servo.h."
        ),
        "ejemplo": (
            "al iniciar\n"
            "configurar servo pin 9"
        ),
        "cpp": (
            "#include <Servo.h>\n"
            "Servo __servoIntegrated;\n"
            "// en setup():\n"
            "__servoIntegrated.attach(9);"
        ),
        "notas": "Un solo servo por sketch. Usa el pin PWM recomendado para tu placa.",
        "placas": "Todas",
    },
    {
        "nombre": "girar servo",
        "categoria": "Servo",
        "sintaxis": "girar servo a angulo",
        "descripcion": (
            "Mueve el servo al angulo indicado (0-180 grados). "
            "Debe haberse configurado primero con 'configurar servo pin N'."
        ),
        "ejemplo": (
            "variable entero = pos\n\n"
            "al iniciar\n"
            "configurar servo pin 9\n\n"
            "repetir siempre\n"
            "girar servo a 0\n"
            "esperar 500\n"
            "girar servo a 90\n"
            "esperar 500\n"
            "girar servo a 180\n"
            "esperar 500"
        ),
        "cpp": (
            "__servoIntegrated.write(0);\n"
            "delay(500);\n"
            "__servoIntegrated.write(90);\n"
            "delay(500);\n"
            "__servoIntegrated.write(180);\n"
            "delay(500);"
        ),
        "notas": "Valores fuera de 0-180 pueden dañar el servo.",
        "placas": "Todas",
    },

    # ── ULTRASONIDO ───────────────────────────────────────────────────────────
    {
        "nombre": "configurar ultrasonido",
        "categoria": "Ultrasonido",
        "sintaxis": "configurar ultrasonido trig N echo M",
        "descripcion": (
            "Configura un sensor ultrasonido HC-SR04. "
            "El pin TRIG envia el pulso y el pin ECHO lo recibe. "
            "Esta linea configura los modos de los pines automaticamente."
        ),
        "ejemplo": (
            "al iniciar\n"
            "configurar ultrasonido trig 12 echo 13"
        ),
        "cpp": (
            "pinMode(12, OUTPUT);\n"
            "pinMode(13, INPUT);"
        ),
        "notas": "El HC-SR04 trabaja a 5V. Usa divisor de voltaje si usas ESP32 (3.3V).",
        "placas": "Todas",
    },
    {
        "nombre": "medir distancia",
        "categoria": "Ultrasonido",
        "sintaxis": "medir distancia en variable",
        "descripcion": (
            "Dispara el sensor ultrasonido y guarda la distancia medida en centimetros "
            "en la variable indicada. Requiere haber configurado el sensor antes."
        ),
        "ejemplo": (
            "variable decimal = distancia\n\n"
            "al iniciar\n"
            "configurar ultrasonido trig 12 echo 13\n\n"
            "repetir siempre\n"
            "medir distancia en distancia\n"
            "escribe Distancia cm , distancia\n"
            "si distancia es menor a 20\n"
            "escribe Obstaculo detectado\n"
            "fin si\n"
            "esperar 100"
        ),
        "cpp": (
            "digitalWrite(12, LOW);\n"
            "delayMicroseconds(2);\n"
            "digitalWrite(12, HIGH);\n"
            "delayMicroseconds(10);\n"
            "digitalWrite(12, LOW);\n"
            "{ long __dur = pulseIn(13, HIGH); distancia = __dur * 0.0343 / 2.0; }"
        ),
        "notas": "Rango efectivo: 2-400 cm. Evita objetos blandos o angulos oblicuos.",
        "placas": "Todas",
    },

    # ── MOTORES ───────────────────────────────────────────────────────────────
    {
        "nombre": "configurar motor",
        "categoria": "Motores",
        "sintaxis": "configurar motor (izquierdo|derecho|a|b) pwm P in1 I in2 J",
        "descripcion": (
            "Configura un motor DC con puente H (L298N o similar). "
            "Especifica el pin PWM para velocidad y los pines IN1/IN2 para direccion."
        ),
        "ejemplo": (
            "al iniciar\n"
            "configurar motor izquierdo pwm 5 in1 6 in2 7\n"
            "configurar motor derecho pwm 9 in1 10 in2 11"
        ),
        "cpp": (
            "pinMode(5, OUTPUT);\n"
            "pinMode(6, OUTPUT);\n"
            "pinMode(7, OUTPUT);"
        ),
        "notas": "Nombres validos: izquierdo, derecho, a, b.",
        "placas": "Todas",
    },
    {
        "nombre": "motor (movimiento)",
        "categoria": "Motores",
        "sintaxis": (
            "motor nombre adelante velocidad\n"
            "motor nombre atras velocidad\n"
            "motor nombre parar"
        ),
        "descripcion": (
            "Mueve un motor configurado hacia adelante, atras, o lo detiene. "
            "La velocidad es un valor PWM de 0 a 255 (por defecto 200)."
        ),
        "ejemplo": (
            "repetir siempre\n"
            "motor izquierdo adelante 180\n"
            "motor derecho adelante 180\n"
            "esperar 2000\n"
            "parar motores\n"
            "esperar 1000"
        ),
        "cpp": (
            "digitalWrite(6, HIGH);\n"
            "digitalWrite(7, LOW);\n"
            "analogWrite(5, 180);"
        ),
        "notas": "Si no escribes la velocidad, se usa 200 por defecto.",
        "placas": "Todas",
    },
    {
        "nombre": "parar motores",
        "categoria": "Motores",
        "sintaxis": "parar motores",
        "descripcion": "Detiene todos los motores configurados al mismo tiempo.",
        "ejemplo": (
            "repetir siempre\n"
            "motor izquierdo adelante 200\n"
            "esperar 3000\n"
            "parar motores\n"
            "esperar 1000"
        ),
        "cpp": (
            "digitalWrite(in1, LOW);\n"
            "digitalWrite(in2, LOW);\n"
            "analogWrite(pwm, 0); // repetido por cada motor configurado"
        ),
        "notas": None,
        "placas": "Todas",
    },

    # ── BUZZER / TONO ─────────────────────────────────────────────────────────
    {
        "nombre": "tono pin",
        "categoria": "Buzzer / Tono",
        "sintaxis": "tono pin N frecuencia F duracion D",
        "descripcion": (
            "Genera un tono en el buzzer o altavoz conectado al pin N, "
            "con la frecuencia F en Hz durante D milisegundos."
        ),
        "ejemplo": (
            "al iniciar\n"
            "configurar pin 8, salida\n\n"
            "repetir siempre\n"
            "tono pin 8 frecuencia 440 duracion 500\n"
            "esperar 600\n"
            "tono pin 8 frecuencia 880 duracion 500\n"
            "esperar 600"
        ),
        "cpp": (
            "tone(8, 440, 500);\n"
            "delay(600);\n"
            "tone(8, 880, 500);\n"
            "delay(600);"
        ),
        "notas": (
            "Frecuencias musicales:\n"
            "  Do=262, Re=294, Mi=330, Fa=349,\n"
            "  Sol=392, La=440, Si=494 Hz"
        ),
        "placas": "Todas",
    },
    {
        "nombre": "silencio pin",
        "categoria": "Buzzer / Tono",
        "sintaxis": "silencio pin N",
        "descripcion": "Detiene el tono en el pin indicado (equivale a noTone).",
        "ejemplo": (
            "repetir siempre\n"
            "tono pin 8 frecuencia 1000 duracion 200\n"
            "esperar 1000\n"
            "silencio pin 8\n"
            "esperar 500"
        ),
        "cpp": "noTone(8);",
        "notas": None,
        "placas": "Todas",
    },

    # ── SENSORES ──────────────────────────────────────────────────────────────
    {
        "nombre": "leer humedad suelo",
        "categoria": "Sensores",
        "sintaxis": "leer humedad suelo A0 en variable",
        "descripcion": (
            "Lee un sensor de humedad de suelo conectado al pin analogico. "
            "Mayor valor = suelo mas seco. "
            "Rango: 0-1023 (AVR) o 0-4095 (ESP32)."
        ),
        "ejemplo": (
            "variable entero = humedad\n\n"
            "repetir siempre\n"
            "leer humedad suelo A0 en humedad\n"
            "escribe Humedad suelo , humedad\n"
            "si humedad es mayor a 600\n"
            "hacer que pin 7, encendido\n"
            "fin si\n"
            "esperar 2000"
        ),
        "cpp": "humedad = analogRead(A0);",
        "notas": "Calibra los umbrales segun tu sensor. 600+ suele indicar suelo seco.",
        "placas": "Todas",
    },
    {
        "nombre": "leer temperatura lm35",
        "categoria": "Sensores",
        "sintaxis": "leer temperatura lm35 A1 en variable",
        "descripcion": (
            "Lee el sensor de temperatura LM35 en el pin analogico indicado y "
            "convierte el valor ADC a grados Celsius. "
            "La formula asume 3.3V y ADC de 12 bits (ESP32)."
        ),
        "ejemplo": (
            "variable decimal = temperatura\n\n"
            "repetir siempre\n"
            "leer temperatura lm35 A1 en temperatura\n"
            "escribe Temperatura C , temperatura\n"
            "esperar 2000"
        ),
        "cpp": "temperatura = (analogRead(A1) * (3.3 / 4095.0)) * 100.0;",
        "notas": "Para Arduino 5V con 10 bits: (analogRead(pin) * 5.0 / 1023.0) * 100.0",
        "placas": "Todas (formula optimizada para ESP32)",
    },
    {
        "nombre": "leer luz",
        "categoria": "Sensores",
        "sintaxis": "leer luz A0 en variable",
        "descripcion": (
            "Lee un fotoresistor (LDR) en el pin analogico indicado. "
            "Valores altos = mucha luz, valores bajos = oscuridad."
        ),
        "ejemplo": (
            "variable entero = luz\n\n"
            "repetir siempre\n"
            "leer luz A0 en luz\n"
            "si luz es menor a 300\n"
            "escribe Esta oscuro\n"
            "tono pin 8 frecuencia 500 duracion 100\n"
            "fin si\n"
            "esperar 500"
        ),
        "cpp": "luz = analogRead(A0);",
        "notas": "Conecta el LDR en divisor de voltaje con resistencia de 10k ohm.",
        "placas": "Todas",
    },

    # ── WIFI ──────────────────────────────────────────────────────────────────
    {
        "nombre": "wifi conectar",
        "categoria": "WiFi (ESP32/ESP8266)",
        "sintaxis": 'wifi conectar "nombre" "clave"',
        "descripcion": (
            "Conecta el ESP32 o ESP8266 a una red WiFi existente (modo cliente STA). "
            "Genera codigo de conexion con timeout de 20 segundos, "
            "reconexion automatica y diagnosticos por monitor serie."
        ),
        "ejemplo": (
            "al iniciar\n"
            'wifi conectar "MiRedWiFi" "miClave123"\n'
            "servidor iniciar 80\n\n"
            "repetir siempre\n"
            "servidor atender"
        ),
        "cpp": (
            "WiFi.mode(WIFI_STA);\n"
            "WiFi.disconnect();\n"
            "delay(250);\n"
            "WiFi.setAutoReconnect(true);\n"
            'WiFi.begin("MiRedWiFi", "miClave123");\n'
            "unsigned long __wifiInicio = millis();\n"
            "while (WiFi.status() != WL_CONNECTED && millis() - __wifiInicio < 20000)\n"
            "  { delay(250); }\n"
            "if (WiFi.status() == WL_CONNECTED)\n"
            "  { Serial.println(WiFi.localIP()); }"
        ),
        "notas": (
            "IMPORTANTE: Reemplaza por tu red real.\n"
            "La red debe ser de 2.4 GHz (ESP32/ESP8266 no soportan 5 GHz).\n"
            "Estado 6 en monitor = SSID no encontrado.\n"
            "No compatible con Arduino UNO/MEGA/Nano."
        ),
        "placas": "ESP32, ESP8266",
    },
    {
        "nombre": "wifi nombre / wifi clave / wifi iniciar",
        "categoria": "WiFi (ESP32/ESP8266)",
        "sintaxis": (
            'wifi nombre "MiRed"\n'
            'wifi clave "miClave"\n'
            "wifi iniciar"
        ),
        "descripcion": (
            "Alternativa a 'wifi conectar': define el nombre y la clave en lineas separadas "
            "y luego lanza la conexion con 'wifi iniciar'. "
            "Permite usar variables de texto como credenciales."
        ),
        "ejemplo": (
            "variable texto = red\n"
            "variable texto = clave\n\n"
            "al iniciar\n"
            'asignar red = "MiRedWiFi"\n'
            'asignar clave = "miClave"\n'
            "wifi conectar red clave"
        ),
        "cpp": "WiFi.begin(red.c_str(), clave.c_str());",
        "notas": "Puedes almacenar las credenciales en variables para cambiarlas desde Serial.",
        "placas": "ESP32, ESP8266",
    },
    {
        "nombre": "wifi crear punto de acceso",
        "categoria": "WiFi (ESP32/ESP8266)",
        "sintaxis": 'wifi crear punto de acceso "Nombre" "Clave12345"',
        "descripcion": (
            "Crea una red WiFi propia (modo AP) desde el ESP32/ESP8266. "
            "Los dispositivos se conectan a esta red y acceden a http://192.168.4.1. "
            "Util cuando no hay router disponible."
        ),
        "ejemplo": (
            "al iniciar\n"
            "configurar led integrado\n"
            'wifi crear punto de acceso "MiESP32" "12345678"\n'
            "servidor iniciar 80\n"
            'servidor html "/" "<h1>Hola desde mi ESP32</h1>"\n\n'
            "repetir siempre\n"
            "parpadear led integrado 500\n"
            "servidor atender"
        ),
        "cpp": (
            "WiFi.mode(WIFI_AP);\n"
            'WiFi.softAP("MiESP32", "12345678");\n'
            "Serial.println(WiFi.softAPIP());"
        ),
        "notas": "La clave debe tener al menos 8 caracteres. IP por defecto: 192.168.4.1.",
        "placas": "ESP32, ESP8266",
    },
    {
        "nombre": "wifi mostrar ip / wifi ip en / wifi desconectar",
        "categoria": "WiFi (ESP32/ESP8266)",
        "sintaxis": (
            "wifi mostrar ip\n"
            "wifi ip en variable\n"
            "wifi desconectar"
        ),
        "descripcion": (
            "wifi mostrar ip: imprime la IP local en el Monitor serie.\n"
            "wifi ip en variable: guarda la IP como texto en la variable.\n"
            "wifi desconectar: desconecta el WiFi completamente."
        ),
        "ejemplo": (
            "variable texto = direccion\n\n"
            "repetir siempre\n"
            "wifi ip en direccion\n"
            "escribe IP actual , direccion\n"
            "esperar 5000"
        ),
        "cpp": (
            "direccion = WiFi.localIP().toString();\n"
            'Serial.print("IP actual ");\n'
            "Serial.println(direccion);"
        ),
        "notas": None,
        "placas": "ESP32, ESP8266",
    },

    # ── SERVIDOR WEB ──────────────────────────────────────────────────────────
    {
        "nombre": "servidor iniciar",
        "categoria": "Servidor Web (ESP32/ESP8266)",
        "sintaxis": "servidor iniciar 80",
        "descripcion": (
            "Inicia un servidor HTTP en el puerto indicado (normalmente 80). "
            "Se llama despues de conectar el WiFi o crear un punto de acceso."
        ),
        "ejemplo": (
            "al iniciar\n"
            'wifi conectar "MiRed" "clave"\n'
            "servidor iniciar 80\n"
            'servidor html "/" "<h1>Hola</h1>"\n\n'
            "repetir siempre\n"
            "servidor atender"
        ),
        "cpp": "__servidorIntegrated.begin(80);",
        "notas": "Solo para ESP32 y ESP8266. No compatible con Arduino UNO/MEGA/Nano.",
        "placas": "ESP32, ESP8266",
    },
    {
        "nombre": "servidor html",
        "categoria": "Servidor Web (ESP32/ESP8266)",
        "sintaxis": (
            'servidor html "/ruta" "contenido HTML"\n\n'
            "# Bloque multilinea:\n"
            'servidor html "/ruta":\n'
            "  <html>...</html>\n"
            "fin html\n\n"
            "# Forma explicita para delimitar HTML:\n"
            'contenido html "/ruta":\n'
            "  <html>...</html>\n"
            "fin contenido html"
        ),
        "descripcion": (
            "Registra una ruta HTTP que responde con contenido HTML. "
            "Para HTML corto usalo en una linea. "
            "Para HTML largo usa el bloque multilinea. Puedes delimitarlo con "
            "'servidor html' y 'fin html', o con 'contenido html' y 'fin contenido html'."
        ),
        "ejemplo": (
            'contenido html "/":\n'
            "<!doctype html>\n"
            "<html lang='es'>\n"
            "<head><title>Mi ESP32</title></head>\n"
            "<body><h1>Hola mundo</h1></body>\n"
            "</html>\n"
            "fin contenido html"
        ),
        "cpp": (
            '__servidorIntegrated.on("/", []() {\n'
            '  __servidorIntegrated.send(200, "text/html",\n'
            '    "<!doctype html><html>...</html>");\n'
            "});"
        ),
        "notas": (
            "Para paginas con CSS y JS externos usa 'servidor pagina' con LittleFS.\n"
            "El contenido se incrusta como cadena en el sketch."
        ),
        "placas": "ESP32, ESP8266",
    },
    {
        "nombre": "servidor ruta",
        "categoria": "Servidor Web (ESP32/ESP8266)",
        "sintaxis": 'servidor ruta "/ruta" "texto de respuesta"',
        "descripcion": (
            "Registra una ruta HTTP que responde con texto plano. "
            "Mas simple que servidor html; util para endpoints de API o texto puro."
        ),
        "ejemplo": (
            "al iniciar\n"
            'servidor ruta "/" "Hola desde la placa"\n'
            'servidor ruta "/ping" "pong"'
        ),
        "cpp": (
            '__servidorIntegrated.on("/", []() {\n'
            '  __servidorIntegrated.send(200, "text/html", "Hola desde la placa");\n'
            "});"
        ),
        "notas": None,
        "placas": "ESP32, ESP8266",
    },
    {
        "nombre": "servidor pagina",
        "categoria": "Servidor Web (ESP32/ESP8266)",
        "sintaxis": 'servidor pagina "/ruta" "archivo.html"',
        "descripcion": (
            "Sirve un archivo HTML desde el sistema de archivos LittleFS de la placa. "
            "Util para paginas con CSS, JavaScript e imagenes separados. "
            "El archivo debe estar cargado con la herramienta de filesystem."
        ),
        "ejemplo": (
            "al iniciar\n"
            'wifi conectar "MiRed" "clave"\n'
            "servidor iniciar 80\n"
            'servidor pagina "/" "index.html"\n\n'
            "repetir siempre\n"
            "servidor atender"
        ),
        "cpp": (
            '__servidorIntegrated.on("/", []() {\n'
            '  File __pagina = LittleFS.open("/index.html", "r");\n'
            '  __servidorIntegrated.streamFile(__pagina, "text/html");\n'
            "  __pagina.close();\n"
            "});"
        ),
        "notas": "Requiere cargar el filesystem con la herramienta de LittleFS para tu placa.",
        "placas": "ESP32, ESP8266",
    },
    {
        "nombre": "servidor atender",
        "categoria": "Servidor Web (ESP32/ESP8266)",
        "sintaxis": "servidor atender",
        "descripcion": (
            "Procesa las peticiones HTTP entrantes. "
            "Debe llamarse en 'repetir siempre' para que el servidor responda continuamente. "
            "Si no lo llamas, el servidor no responde a ningun cliente."
        ),
        "ejemplo": (
            "repetir siempre\n"
            "parpadear led integrado 500\n"
            "servidor atender"
        ),
        "cpp": "__servidorIntegrated.handleClient();",
        "notas": "Si no llamas a 'servidor atender' en el loop, el servidor HTTP no funciona.",
        "placas": "ESP32, ESP8266",
    },
    {
        "nombre": "servidor al recibir",
        "categoria": "Servidor Web (ESP32/ESP8266)",
        "sintaxis": (
            'servidor al recibir "/encender" encender pin N y redirigir "/"\n'
            'servidor al recibir "/apagar" apagar pin N y redirigir "/"\n'
            'servidor al recibir "/alternar" alternar pin N y redirigir "/"\n'
            'servidor al recibir "/ruta" responder "mensaje"'
        ),
        "descripcion": (
            "Crea un endpoint HTTP interactivo en el servidor web del ESP32. "
            "Permite encender, apagar o alternar pines con solo acceder a la URL desde un navegador, "
            "ideal para paneles de control IoT desde el teléfono celular o la PC."
        ),
        "ejemplo": (
            "al iniciar\n"
            "configurar pin 15, salida\n"
            'wifi crear punto de acceso "ESP32_Panel" "12345678"\n'
            "servidor iniciar 80\n"
            'servidor al recibir "/encender" encender pin 15 y redirigir "/"\n'
            'servidor al recibir "/apagar" apagar pin 15 y redirigir "/"\n'
            'servidor al recibir "/alternar" alternar pin 15 y redirigir "/"\n\n'
            "repetir siempre\n"
            "servidor atender"
        ),
        "cpp": (
            '__servidorIntegrated.on("/encender", []() {\n'
            '  digitalWrite(15, HIGH);\n'
            '  __servidorIntegrated.sendHeader("Location", "/");\n'
            '  __servidorIntegrated.send(303);\n'
            '});'
        ),
        "notas": "Exclusivo para placas ESP32 y ESP8266.",
        "placas": "ESP32, ESP8266",
    },
]


def lista_categorias() -> list[str]:
    """Devuelve las categorias con comandos disponibles, en el orden definido."""
    usadas = {cmd["categoria"] for cmd in COMANDOS}
    return [c for c in CATEGORIAS_ORDEN if c in usadas]


def comandos_de(categoria: str) -> list[dict]:
    """Devuelve los comandos de una categoria especifica."""
    return [cmd for cmd in COMANDOS if cmd["categoria"] == categoria]


def buscar_comandos(termino: str) -> list[dict]:
    """Busca comandos cuyo nombre, sintaxis o descripcion contengan el termino."""
    t = termino.lower()
    return [
        cmd for cmd in COMANDOS
        if (
            t in cmd["nombre"].lower()
            or t in cmd["sintaxis"].lower()
            or t in cmd["descripcion"].lower()
        )
    ]


def total_comandos() -> int:
    """Devuelve el numero total de comandos en la biblioteca."""
    return len(COMANDOS)
