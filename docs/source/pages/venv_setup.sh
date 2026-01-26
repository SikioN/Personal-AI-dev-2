apt-get update -y
apt-get upgrade -y
echo "=== REFRESHING END ==="

apt install python3.10-venv
apt install libicu-dev python3-icu pkg-config

python3.10 -m venv ../../.pai_venv
source ../../.pai_venv/bin/activate
echo "=== ENV-CREATION END ==="

pip install pysqlite3-binary chromadb==0.5.3 aerospike==15.1.0 kuzu pymongo neo4j redis
pip install dataclasses tqdm joblib
pip install pyicu pycld2 morfessor polyglot
pip install numpy pandas
pip install torch==2.4.1 transformers==4.40.0 sentence_transformers
pip install gigachat==0.1.17 openai ollama
pip install pytest
echo "=== PACKAGES-INSTALLATION END"
