import os
import re
import random
import ipaddress
import subprocess
import concurrent.futures

import requests
from lxml import etree
from fake_useragent import UserAgent
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ips = "Fission_ip.txt"
domains = "Fission_domain.txt"
dns_result = "dns_result.txt"

max_workers_request = 20
max_workers_dns = 50

ua = UserAgent()

sites_config = {
    "site_ip138": {
        "url": "https://site.ip138.com/",
        "xpath": '//ul[@id="list"]/li/a'
    },
    "dnsdblookup": {
        "url": "https://dnsdblookup.com/",
        "xpath": '//ul[@id="list"]/li/a'
    },
    "ipchaxun": {
        "url": "https://ipchaxun.com/",
        "xpath": '//div[@id="J_domain"]/p/a'
    }
}

def setup_session():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def get_headers():
    return {
        'User-Agent': ua.random,
        'Accept': '*/*',
        'Connection': 'keep-alive',
    }

def fetch_domains_for_ip(ip_address, session, attempts=0, used_sites=None):
    print(f"Fetching domains for {ip_address}...")
    if used_sites is None:
        used_sites = []
    if attempts >= 3:
        return []

    available_sites = {key: value for key, value in sites_config.items() if key not in used_sites}
    if not available_sites:
        return []

    site_key = random.choice(list(available_sites.keys()))
    site_info = available_sites[site_key]
    used_sites.append(site_key)

    try:
        url = f"{site_info['url']}{ip_address}/"
        headers = get_headers()
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        html_content = response.text

        parser = etree.HTMLParser()
        tree = etree.fromstring(html_content, parser)
        a_elements = tree.xpath(site_info['xpath'])
        domains = [a.text for a in a_elements if a.text]

        if domains:
            print(f"succeed to fetch domains for {ip_address} from {site_info['url']}")
            return domains
        else:
            raise Exception("No domains found")

    except Exception as e:
        print(f"Error fetching domains for {ip_address} from {site_info['url']}: {e}")
        return fetch_domains_for_ip(ip_address, session, attempts + 1, used_sites)

def fetch_domains_concurrently(ip_addresses):
    session = setup_session()
    domains = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers_request) as executor:
        future_to_ip = {executor.submit(fetch_domains_for_ip, ip, session): ip for ip in ip_addresses}
        for future in concurrent.futures.as_completed(future_to_ip):
            domains.extend(future.result())
            if len(domains) >= 100:  # 限制域名数量不超过100
                break

    return list(set(domains))[:100]  # 返回最多100个域名

def dns_lookup(domain):
    print(f"Performing DNS lookup for {domain}...")
    result = subprocess.run(["nslookup", domain], capture_output=True, text=True)
    return domain, result.stdout

def perform_dns_lookups(domain_filename, result_filename, unique_ipv4_filename):
    try:
        with open(domain_filename, 'r') as file:
            domains = file.read().splitlines()

        max_ips = 10000
        ipv4_addresses = set()

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers_dns) as executor:
            results = list(executor.map(dns_lookup, domains))

            for domain, output in results:
                if len(ipv4_addresses) >= max_ips:
                    break

                ipv4_addresses.update(re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', output))

        with open(result_filename, 'w') as output_file:
            for domain, output in results:
                output_file.write(output)

        with open(unique_ipv4_filename, 'r') as file:
            exist_list = {ip.strip() for ip in file}

        filtered_ipv4_addresses = set()
        for ip in ipv4_addresses:
            try:
                ip_obj = ipaddress.ip_address(ip)
                if ip_obj.is_global:
                    filtered_ipv4_addresses.add(ip)
            except ValueError:
                continue

        filtered_ipv4_addresses.update(exist_list)

        with open(unique_ipv4_filename, 'w') as output_file:
            for address in filtered_ipv4_addresses:
                output_file.write(address + '\n')

    except Exception as e:
        print(f"Error performing DNS lookups: {e}")

def main():
    if not os.path.exists(ips):
        with open(ips, 'w') as file:
            file.write("")

    if not os.path.exists(domains):
        with open(domains, 'w') as file:
            file.write("")

    with open(ips, 'r') as ips_txt:
        ip_list = [ip.strip() for ip in ips_txt]

    domain_list = fetch_domains_concurrently(ip_list)
    print("域名列表为")
    print(domain_list)
    with open("Fission_domain.txt", "r") as file:
        exist_list = [domain.strip() for domain in file]

    domain_list = list(set(domain_list + exist_list))

    with open("Fission_domain.txt", "w") as output:
        for domain in domain_list:
            output.write(domain + "\n")
    print("IP -> 域名 已完成")

    perform_dns_lookups(domains, dns_result, ips)
    print("域名 -> IP 已完成")

if __name__ == '__main__':
    main()
