import os

def check_files(server="None"):
    failed=[]
    for file in os.listdir("data"):
        if file.startswith(server) or server=="":
            with open(os.path.join("data",file), 'rb') as f:
                f.seek(-2, os.SEEK_END)
                while f.read(1) != b' ':
                    f.seek(-2, os.SEEK_CUR)
                last_line = f.readline().decode()
                try: int(last_line)
                except: failed.append(f"{file} ||| {last_line}")

    assert failed == [], f"Some files in data directory are incomplete downloads:"+"\n".join(failed)
    return "All files passed."

print(check_files(server="a crumb"))