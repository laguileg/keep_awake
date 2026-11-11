# Keep Awake

Pequeño programa para **mantener un equipo Windows activo** durante procesos largos (cargas de datos, descargas, respaldos, renders): evita que el sistema se suspenda o hiberne y, si quieres, que se apague la pantalla. Mientras está abierto, el equipo no duerme; al cerrarlo, todo vuelve a la normalidad.

Usa la API nativa de Windows `SetThreadExecutionState`, la misma que usan PowerToys Awake o Caffeine. **No mueve el mouse ni simula teclas**, y no necesita librerías externas.

Opcionalmente genera un **pulso de red periódico** para que una VPN no se desconecte por falta de tráfico.

## Instalación (Windows, cmd)

```bat
git clone https://github.com/laguileg/keep_awake.git
cd keep_awake
```

No requiere `pip install`: basta con Python 3.10 o superior.

## Uso

```bat
py keep_awake.py
keep_awake.bat
py keep_awake.py --help
```

`keep_awake.bat` permite abrirlo con doble clic desde el Explorador. Para detenerlo: **Ctrl+C** o cerrar la ventana.

## Configuración (`keep_awake.ini`)

La primera vez que se ejecuta, crea `keep_awake.ini` junto al script (o al `.exe`) con valores por defecto. Edítalo y vuelve a abrir el programa; no hace falta recompilar.

| Sección / parámetro | Por defecto | Qué hace |
|---|---|---|
| `[general] keep_display_on` | `true` | Mantiene también la pantalla encendida |
| `[general] refresh_interval_sec` | `30` | Cada cuántos segundos reafirma el estado "activo" |
| `[general] max_runtime_min` | `0` | Minutos máximos de ejecución (0 = sin límite) |
| `[general] log_to_file` / `log_file` | `true` / `keep_awake.log` | Registro de actividad en archivo |
| `[network_keepalive] enabled` | `false` | Activa el pulso de red para la VPN |
| `[network_keepalive] host` / `port` | `8.8.8.8` / `53` | Destino del pulso. Para una VPN, usa un servidor **interno** de tu red |
| `[network_keepalive] interval_sec` | `60` | Cada cuántos segundos se envía el pulso |
| `[network_keepalive] timeout_sec` | `5` | Espera máxima de cada pulso |

> `keep_awake.ini` está excluido del repositorio (`.gitignore`) porque suele contener IPs o servidores de tu red. Nunca lo subas.

## Archivos que genera

- `keep_awake.ini`: tu configuración local, creada en el primer arranque.
- `keep_awake.log`: registro de actividad, si `log_to_file = true`.

## Crear un .exe (opcional)

```bat
py -m pip install pyinstaller
pyinstaller keep_awake.spec
```

El ejecutable queda en `dist\keep_awake.exe`. Copia el `.exe` donde quieras: el `.ini` se crea a su lado.

## Problemas conocidos

- **Solo funciona en Windows.** En otros sistemas avisa y termina.
- **No evita que se bloquee la sesión** si una política de la empresa lo exige: solo impide la suspensión por inactividad.
- **Cerrar la tapa de un notebook** sigue la configuración de energía de Windows, no la de este programa.

## Licencia

[MIT](LICENSE): puedes usar, modificar y compartir este código libremente, manteniendo el aviso de autoría.

## Historial

| Fecha | Versión | Cambios |
|---|---|---|
| 2026-11-11 | 1.0.0 | Primera versión pública: API nativa de Windows sin dependencias, configuración en `.ini`, pulso de red opcional para VPN, ayuda en español (`--help`) y `--version`. Se retiran los archivos de la versión anterior basada en `pyautogui` (`config.json`, `install.sh`). |
