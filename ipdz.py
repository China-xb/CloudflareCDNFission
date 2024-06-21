import os
import glob
import re
import geoip2.database

# 读取IPv4地址的文件
def read_ips(filename):
    with open(filename, 'r') as file:
        return [line.strip() for line in file if line.strip()]

# 使用geoip2获取IP的国家代码
def get_country_code(ip, reader):
    try:
        response = reader.country(ip)
        return response.country.iso_code
    except Exception as e:
        print(f"Error fetching data for IP {ip}: {e}")
        return 'Unknown'

# 保存IP到对应的国家代码文件，并去除重
def save_ip_to_file(ip, country_code):
    country_code = country_code or 'Unknown'
    filename = f'{country_code}.txt'
    
    # 确保文件存在，如果不存在则创建它
    if not os.path.exists(filename):
        open(filename, 'a').close()
    
    # 现在文件肯定存在，我们可以安全地打开它并检查内容
    with open(filename, 'r') as file:
        lines = file.readlines()
    
    # 确保不会重复写入相同的IP地址
    if ip + '\n' not in lines:
        with open(filename, 'a') as file:
            file.write(ip + '\n')


# 删除所有以国家代码命名的.txt文件，除了特定的文件
def delete_existing_country_files(exceptions):
    # 定义国家代码的正则表达式模式
    country_code_pattern = r'[A-Z]{2}\.txt$'
    
    # 遍历当前目录中的所有.txt文件
    for file in glob.glob('*.txt'):
        # 检查文件是否在排除列表中或是否符合国家代码模式
        if file in exceptions or re.match(country_code_pattern, file):
            continue
        os.remove(file)

# 主函数
def main():
    # 指定不删除的文件列表
    exceptions = ['requirements.txt', 'dns_result.txt', 'Fission_domain.txt', 'Fission_ip.txt']

    # 删除所有现有的国家代码文件，除了指定的文件
    delete_existing_country_files(exceptions)

    # 指定GeoLite2数据库文件的路径
    database_path = 'GeoLite2-Country.mmdb'
    with geoip2.database.Reader(database_path) as reader:
        ips = read_ips('Fission_ip.txt')
        for ip in ips:
            country_code = get_country_code(ip, reader)
            save_ip_to_file(ip, country_code)

if __name__ == '__main__':
    main()
