# QuickClipper
Ctrl+Alt+1〜5 のショートカットで、OBS のリプレイバッファを即座にクリップ保存するツール

---

## 主な機能
- Ctrl+Alt+1〜5 のグローバルホットキーでワンタッチ保存
- 15秒 / 30秒 / 60秒 / 5分 / 15分 のプリセット
- クリップ完了時に **サムネイル付きのオーバーレイ通知** を表示
- OBS WebSocket（例：ポート 4455）経由で動作

---

## 使い方（基本的な流れ）

1. ZIP を解凍して **QuickClipper.exe** を起動
2. OBS を起動し、**WebSocket を有効化**（ポート例：4455）
3. **OBS の「リプレイバッファ」を開始**
   ※ QuickClipper からも開始できます
4. QuickClipper の **Settings** タブで OBS の接続情報を入力
5. 以下のショートカットで即クリップ保存：

| ショートカット | 内容 |
|----------------|------|
| Ctrl+Alt+1 | 直近 15秒 |
| Ctrl+Alt+2 | 直近 30秒 |
| Ctrl+Alt+3 | 直近 1分 |
| Ctrl+Alt+4 | 直近 5分 |
| Ctrl+Alt+5 | 直近 15分 |

---

# 🔧 **OBS 側で必ず設定する項目（重要）**

QuickClipper は OBS のリプレイバッファを使用します。
**リプレイバッファの最大記録時間は OBS 側で設定された値に依存します。**

そのため、以下の方法で OBS の設定を行う必要があります。

---

## 🔧 **OBS のリプレイバッファ最大時間の設定方法**

1. OBS を起動
2. メニューから
   **「設定」 → 「出力」 → 「リプレイバッファ」** を開く
3. 以下を確認・設定

   - ✔ **リプレイバッファを有効化**
   - ✔ **最大時間（秒）** → `900`（または任意の秒数）

4. OK を押して設定を保存
5. OBS のメイン画面で **「リプレイバッファを開始」** を押す
   （または QuickClipper に開始させることも可能）

---

## 📝 補足説明
- QuickClipper の最大プリセットは **15分（900秒）** ですが、
  実際に保存できる長さは **OBS のリプレイバッファ最大時間に依存** します。
- たとえば OBS 側が 600 秒（10分）に設定されている場合、
  Ctrl+Alt+5（15min）を押しても **直近 600 秒** までしか保存されません。
- 逆に、OBS の最大時間を 900 秒に設定しておけば、
  全てのプリセット（15秒〜15分）がそのまま利用できます。
- パフォーマンス優先で **120〜300 秒程度に短く設定**することも可能です。
  その場合、15 分プリセットは **指定時間ではなく OBS の最大時間に自動短縮**されます。

---

# 🛠 推奨設定例

| 目的 | OBS 側 最大時間設定 | 利点 |
|-----|----------------------|------|
| QuickClipper を最大限活用 | **900 秒（15分）** | 全プリセット使用可 |
| パフォーマンス優先 | **300〜600 秒** | メモリ負荷・CPU負荷の低減 |
| 短いクリップのみ | **60〜120 秒** | 軽量で安定 |

---

# ⚠ トラブルシューティング

### ■ Ctrl+Alt+5（15min）が保存できない
OBS 側の最大時間が **900 秒未満**になっています。
設定 → 出力 → リプレイバッファ をご確認ください。

---

### ■ 「OBS が録画中のためリプレイバッファを開始できません」
OBS は「録画」と「リプレイバッファ」の同時利用に制限がある設定があります。
録画を停止してから QuickClipper を使用してください。

---

### ■ 「OBS へ接続できません」
以下の原因が考えられます：

- OBS が起動していない
- WebSocket が無効になっている
- ポート番号が一致していない
- パスワードが間違っている

QuickClipper の Settings タブで設定を確認してください。

---

# 動作環境

### 対応 OS
- Windows 10 / Windows 11

### 必須ソフトウェア
- **OBS Studio（Windows版）**
  - OBS 28 以降推奨（WebSocket 標準搭載）
  - **リプレイバッファ機能が有効であること**

- **OBS WebSocket**
  - OBS 28 以降：標準同梱
  - デフォルトポート：4455

### 必須ランタイム / ツール
- **ffmpeg / ffprobe（Windows版）**
  - アプリに同梱されたバイナリ、またはユーザー設定のパスを使用

---

## License

This software is licensed under the **GNU General Public License v3 (GPLv3)**.
See the [LICENSE](./LICENSE) file for details.

### FFmpeg License Notice

This application **bundles a binary build of FFmpeg**, which is licensed under the **GPLv3**.
Because FFmpeg is licensed under GPLv3, this entire application is also distributed
under the terms of the GPLv3 license.

The FFmpeg project is copyright © the FFmpeg developers.
Source code is available at: https://ffmpeg.org/

This distribution includes the following FFmpeg license files:
- `ffmpeg/LICENSE` (GPLv3)
- Any additional license or README files included in the original FFmpeg build

### Third-party libraries

This software uses additional third-party Python libraries (obs-websocket-py, Pillow, pywin32, etc.),
which are each included under their respective licenses (MIT, Apache, PSF, etc.).  
These are all compatible with GPLv3 when distributed alongside this software.

A full list is available in `THIRD_PARTY_NOTICES.txt`.
