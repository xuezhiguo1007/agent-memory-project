#!/bin/bash
# PostgreSQL 数据库初始化脚本

# 数据库配置
DB_NAME="langmem_db"
DB_USER="langmem_user"
DB_PASSWORD="langmem_password"

echo "========================================"
echo "Langmem PostgreSQL 数据库初始化脚本"
echo "========================================"

# 检查 PostgreSQL 是否已安装
if ! command -v psql &> /dev/null; then
    echo "错误: PostgreSQL 未安装"
    echo "请先安装 PostgreSQL:"
    echo "  macOS: brew install postgresql"
    echo "  Ubuntu: sudo apt-get install postgresql"
    exit 1
fi

echo "PostgreSQL 已安装 ✓"

# 创建数据库和用户
echo ""
echo "正在创建数据库和用户..."

# 创建用户
psql -U postgres -c "DO \$\$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${DB_USER}') THEN
        CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
    END IF;
END \$\$;" || echo "用户 ${DB_USER} 已存在"

# 创建数据库
psql -U postgres -c "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}'" | grep -q 1 || \
psql -U postgres -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

echo "数据库 ${DB_NAME} 创建成功 ✓"

# 授权
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"

echo "权限授予成功 ✓"

# 测试连接
echo ""
echo "正在测试数据库连接..."
PGPASSWORD=${DB_PASSWORD} psql -U ${DB_USER} -d ${DB_NAME} -c "SELECT version();" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "数据库连接成功 ✓"
    echo ""
    echo "========================================"
    echo "初始化完成！"
    echo "========================================"
    echo ""
    echo "数据库连接信息:"
    echo "  Host: localhost"
    echo "  Port: 5432"
    echo "  Database: ${DB_NAME}"
    echo "  User: ${DB_USER}"
    echo "  Password: ${DB_PASSWORD}"
    echo ""
    echo "表结构将在第一次使用时自动创建"
    echo ""
else
    echo "错误: 无法连接到数据库"
    echo "请检查 PostgreSQL 是否正在运行"
    echo "启动 PostgreSQL:"
    echo "  macOS: brew services start postgresql"
    echo "  Ubuntu: sudo systemctl start postgresql"
    exit 1
fi