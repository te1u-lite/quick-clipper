# QuickClipper
Ctrl+Alt+1〜5 のショートカットで、OBS のリプレイバッファを即座にクリップ保存するツール

## 主な機能
- Ctrl+Alt+1〜5 のグローバルホットキーでワンタッチ保存
- 15秒 / 30秒 / 60秒 / 5分 / 15分
- クリップ完了時に サムネイル付きのオーバーレイ通知 を表示
- OBS WebSocket（例：ポート 4455）経由で動作


## 使い方
1. ZIP を解凍して **QuickClipper.exe** を起動
2. OBS で WebSocket を有効化（ポート例：4455）
3. OBS の「リプレイバッファ」を開始
4. QuickClipper の Settings タブで接続情報を入力
5. 以下のショートカットで即クリップ保存：
   - Ctrl+Alt+1 → 直近 15秒
   - Ctrl+Alt+2 → 直近 30秒
   - Ctrl+Alt+3 → 直近 1分
   - Ctrl+Alt+4 → 直近 5分
   - Ctrl+Alt+5 → 直近 15分

## 動作環境
### 対応 OS
- Windows 10 / Windows 11

### 必須ソフトウェア
- OBS Studio（Windows版）
    - OBS 28 以降推奨（WebSocket が標準同梱）
    - リプレイバッファ 機能が有効であること
- OBS WebSocket
    - OBS 28 以降：標準同梱
    - デフォルトポート：4455

### 必須ランタイム / ライブラリ
- ffmpeg / ffprobe（Windows版）
