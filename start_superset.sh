#!/bin/bash
# Script khởi động Apache Superset

echo "🚀 Khởi động Apache Superset..."
echo "🌐 Truy cập tại: http://localhost:8088"
echo "📝 Login: admin / admin"
echo ""

export FLASK_APP=superset
superset run -h 0.0.0.0 -p 8088 --with-threads --reload --debugger
