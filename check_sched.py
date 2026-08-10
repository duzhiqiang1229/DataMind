# -*- coding: utf-8 -*-
import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.1.4", port=22, username="root", password="slwy", timeout=15)


def run(cmd):
    _, stdout, stderr = client.exec_command(cmd, timeout=30)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    print(f"$ {cmd}")
    if out.strip():
        print(out.rstrip()[:1500])
    if err.strip():
        print("STDERR:", err.rstrip()[:500])
    print()


run("python3 -c \"print(open('/home/airflow/dags/etl_schedule_etl_pyspark_6a29b67b.py', 'rb').read()[:60])\"")
run("grep -n 'etl_schedule' /home/airflow/logs/scheduler/*/*.log 2>/dev/null | tail -5")
run("airflow dags list 2>/dev/null | grep -i 'etl_schedule\\|Total dags'")

client.close()
