#!/bin/bash
# Script cài đặt Apache Superset trong Hadoop master container

echo "🚀 Bắt đầu cài đặt Apache Superset..."

# Cập nhật pip
pip3 install --upgrade pip

# Cài đặt dependencies
apt-get update
apt-get install -y build-essential libssl-dev libffi-dev python3-dev libsasl2-dev libldap2-dev

# Cài đặt Superset
pip3 install apache-superset

# Cài đặt database drivers
pip3 install psycopg2-binary  # PostgreSQL
pip3 install trino            # Trino connector
pip3 install sqlalchemy-trino # SQLAlchemy driver cho Trino

# Khởi tạo database
export FLASK_APP=superset
superset db upgrade

# Tạo admin user (username: admin, password: admin)
superset fab create-admin \
    --username admin \
    --firstname Admin \
    --lastname User \
    --email admin@superset.com \
    --password admin

# Load example data (optional)
# superset load_examples

# Khởi tạo roles và permissions
superset init

echo "✅ Cài đặt Superset hoàn tất!"
echo "📝 Thông tin đăng nhập:"
echo "   Username: admin"
echo "   Password: admin"
echo ""
echo "🌐 Để khởi động Superset, chạy lệnh:"
echo "   superset run -h 0.0.0.0 -p 8088 --with-threads --reload --debugger"
