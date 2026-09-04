# セットアップと再現手順

## 1. OSとI²C

Raspberry Pi OSを更新し、`raspi-config`でI²Cを有効にします。SSD1306がI²Cバスで認識されることを確認してください。

## 2. Python環境

この構成ではOS標準のPython 3と、次の機能を使用します。

- gpiozero
- pigpio / pigpiod
- Pillow
- luma.oled

ディストリビューションのパッケージ管理機能から導入し、`pigpiod`を起動します。パッケージ名は使用中のRaspberry Pi OSで確認してください。

## 3. 段階的な確認

1. `examples/oled/oled_ssd1306_demo.py`でOLEDだけを確認
2. `src/hc_sr04_test.py`で距離測定だけを確認
3. `src/sg90_set_angle.py`で中央付近を確認
4. `src/sg90_motion_test.py`で安全範囲を確認
5. `src/hc_sr04_oled_test.py`で固定表示を確認
6. `src/hc_sr04_radar_test_v4.py`で統合動作を確認

## 4. 完成版の実行

```bash
python3 src/hc_sr04_radar_test_v4.py
```

本機ではSG90を`500µs=0度`、`1500µs=90度`、`2500µs=180度`として校正しました。別個体へそのまま適用せず、中央付近から再校正してください。

TIMEOUTや外れ値が増える場合は、測距間隔を75ms未満へ短縮せず、反射物、センサー角度、電源、配線を確認します。
