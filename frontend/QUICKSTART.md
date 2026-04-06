# 🚀 Quick Start - Execution Dashboard

## 1️⃣ Instalação Rápida (30 segundos)

```bash
# Terminal na pasta do projeto
cd frontend

# Instale dependências (apenas na primeira vez)
pip install flask flask-cors

# Pronto!
```

## 2️⃣ Iniciar o Dashboard

### Windows
```bash
start-server.bat
```

### Linux/Mac
```bash
bash start-server.sh
```

### Manual
```bash
python api.py
```

## 3️⃣ Abrir no Navegador

```
http://localhost:5000
```

## ✨ Pronto para usar!

Você verá:
- ✅ Lista de todas as execuções
- 📊 Estatísticas (total, sucesso, falhas)
- 🔄 Botão de atualizar
- 📋 Detalhes completos de cada execução
- 🖼️ Screenshots em galeria
- 📝 Logs de execução
- 📊 Dados em JSON

---

## 🎯 O que você pode fazer

### 1. Visualizar Execuções
- Veja a lista de todas as execuções ordenadas por data
- Status badges mostram sucesso/falha
- Informações rápidas em cada card

### 2. Ver Detalhes
- Clique em qualquer execução para expandir
- Veja resumo completo
- Analise screenshots em tela cheia
- Leia logs de debug

### 3. Exportar Dados
- Copie o JSON de qualquer execução
- Use a API para integrar com outros sistemas
- Faça scripts para processar dados

---

## 🔗 Links Úteis

- **README.md** - Documentação completa
- **API_EXAMPLES.md** - Exemplos de como usar a API
- **DEVELOPMENT.md** - Guia para desenvolvedores

---

## ❓ Problemas?

### Porta em uso?
```bash
# Edite api.py e mude a porta:
# app.run(host="0.0.0.0", port=5001)
```

### Sem execuções?
- Verifique se a pasta `logs` existe no diretório pai
- Confirme que há arquivos `summary.json` nas subpastas

### Screenshots não carregam?
- Confirme que PNG/JPG files existem nas pastas
- Verifique as permissões de leitura

---

## 📚 Próximos Passos

1. ✅ Explore o dashboard
2. 📖 Leia a documentação completa em README.md
3. 🔌 Conheça a API em API_EXAMPLES.md
4. 🛠️ Customize conforme necessário (veja DEVELOPMENT.md)

**Aproveite! 🎉**
