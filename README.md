# magazine-crawler

## 環境構築手順

```bash
git clone https://github.com/ytgw/magazine-crawler.git

# TwitterのAPIキーなどを配置
# config/docker-compose.envを配置

# crontab設定
sudo crontab -e
# 日本時間の深夜0時過ぎに実行
# 21 15 * * * docker compose --file /your-path/docker-compose.yml up --pull always

# 動作確認
docker compose --file /your-path/docker-compose.yml up --pull always
```
