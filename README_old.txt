

Dependencias:

pip install --upgrade pip pyserial pillow esptool pyinstaller



En MAC

Compilar:

pyinstaller kodeOSmac.spec

Crear DMG:

brew install create-dmg
create-dmg \
  --volname "KodeOS Loader" \
  --window-pos 200 120 \
  --window-size 540 380 \
  --icon-size 120 \
  --icon "kodeOS.app" 120 160 \
  --app-drop-link 420 160 \
  dist/kodeOS_Loader.dmg \
  dist/kodeOS.app



En windows:

pyinstaller kodeOSwindows.spec



Generar BIN del codigo:

Ir a ruta de build

python $IDF_PATH/components/esptool_py/esptool/esptool.py \
  --chip esp32s3 merge_bin \
  -o nombredelcodigo.bin \
  --flash_mode dio --flash_freq 80m --flash_size 16MB \
  0x0      bootloader/bootloader.bin \
  0x8000   partition_table/partition-table.bin \
  0x10000  ota_data_initial.bin \
  0x20000  kodeOS.bin


python3 -m esptool --chip esp32s3 merge_bin \
  -o nombredelcodigo.bin \
  --flash_mode dio --flash_freq 80m --flash_size 16MB \
  0x0      bootloader/bootloader.bin \
  0x8000   partition_table/partition-table.bin \
  0x10000  ota_data_initial.bin \
  0x20000  kodeOS.bin




