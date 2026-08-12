# CDMX BayesOpt

🇲🇽 [Español](README.md) · 🇬🇧 [English](README.en.md)

Experimento ligero de optimización bayesiana para una Radxa ZERO 3W de 1 GB.
El NeoPixel ilumina una superficie, el TCS34725 mide el color reflejado y
BayesOpt ajusta **rojo, verde y azul** para acercarse a un color objetivo.

## Taller

En la terminal de la Radxa:

```bash
./get-bayesopt-code
cd cdmx-bayesopt
./scripts/install-color-lab.sh
```

Abra `http://equipoN.local:8010/`. La página muestra la reflexión en RGB y
hexadecimal, y permite probar colores en el LED. Después ejecute una campaña
con **una sola entrada**, el color reflejado deseado:

```bash
./scripts/run-color-campaign.sh '#4A80C0'
# también acepta: ./scripts/run-color-campaign.sh '74,128,192'
```

Siga los experimentos en `http://equipoN.local:8000/`. Un valor objetivo más
bajo significa una mejor coincidencia. `Ctrl-C` detiene la campaña.

Coloque el LED y el sensor apuntando a la **misma zona de la superficie**, sin
que el LED ilumine directamente el sensor.

## Cableado (placa apagada)

| Dispositivo | Señal | Pin físico |
|---|---|---:|
| TCS34725 | VCC / GND / SCL / SDA | **4 / 6 / 8 / 10** |
| NeoPixel | VCC / DIN / GND | **2 / 19 / 20** |

Los pines 8/10 usan el adaptador `i2c-gpio-cdmx`; el pin 19 usa `SPI3_MOSI`.
Se recomienda un conversor lógico 74AHCT125 o 74HCT245 para DIN cuando el
NeoPixel se alimenta con 5 V.

## Instalación sin la imagen del taller

```bash
git clone https://github.com/the-matter-lab/cdmx-bayesopt.git
cd cdmx-bayesopt
./scripts/install-color-lab.sh
grep -qhs 'i2c-gpio-cdmx' /sys/class/i2c-dev/i2c-*/name || sudo reboot
```

El servicio vuelve a iniciar después de apagar/encender la Radxa. Diagnóstico:

```bash
systemctl status cdmx-color-lab
journalctl -u cdmx-color-lab -n 50 --no-pager
```

Sin hardware, pruebe la interfaz con:

```bash
./scripts/run-color-lab.sh --simulate
# http://localhost:8010/
```

La demo matemática 2D sigue disponible con `./scripts/run-demo.sh`. Las salidas
de cada campaña quedan en `runs/` como CSV, JSON, gráficas y GIF.

## Desarrollo

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --editable '.[visual]'
make test
```

La interfaz local no tiene autenticación: úsela solamente en una LAN de
confianza. Proyecto inspirado por
[`self-driving-lab-demo`](https://github.com/sparks-baird/self-driving-lab-demo);
licencia y atribución en [`LICENSE`](LICENSE) y [`NOTICE.md`](NOTICE.md).
