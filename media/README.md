# Release配布用メディア

このフォルダのMOVはGitで追跡せず、`v1.0.0-radar-demo` Releaseの添付ファイルとして配布します。

| Release asset | 内容 |
|---|---|
| `radar-sweep-oled-demo-v1.0.0.mov` | HC-SR04、SG90、SSD1306 OLEDを統合した走査レーダーの全体動作 |
| `radar-oled-display-demo-v1.0.0.mov` | 2mスケールのOLEDレーダー表示のクローズアップ |

公開時は[リリース公開スクリプト](../scripts/publish-release.ps1)を使うか、GitHubのRelease画面で上の2ファイルを同じタグへ添付します。リリースノートは[release-notes-v1.0.0-radar-demo.md](release-notes-v1.0.0-radar-demo.md)です。

動画には音声トラックがあります。公開前に音声、映り込み、位置情報、端末情報などのメタデータを確認してください。
