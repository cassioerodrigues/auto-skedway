# Auto Skedway - Deployment em Subpath com Nginx

## Problema
Sua aplicação rodava em `cassiorodrigues.tech/skedway/` mas os dados não funcionavam.

## Causa
O Flask não estava configurado para confiar nos headers do proxy nginx, o que causava problemas com:
- Referências de IP real
- protocolo correto (http/https)
- Host correto para CORS e redirects

## Solução Aplicada

### 1. Flask Backend - ProxyFix (✅ Já Aplicado)
Adicionado em `frontend/api.py`:
```python
from werkzeug.middleware.proxy_fix import ProxyFix

app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,      # Confia em X-Real-IP / X-Forwarded-For
    x_proto=1,    # Confia em X-Forwarded-Proto (http/https)
    x_host=1,     # Confia em X-Forwarded-Host
    x_prefix=1    # Confia em X-Forwarded-Prefix (para /skedway/)
)
```

**O que faz:** Instrui o Flask a ler corretamente os headers enviados pelo nginx.

### 2. Nginx Configuration (⚠️ Você Precisa Aplicar)
Arquivo: `nginx-config.conf` (ou seu arquivo nginx original)

**Pontos-chave:**
- `X-Forwarded-Prefix /skedway` - diz ao Flask onde a app está rodando
- `X-Forwarded-Proto $scheme` - garante protocolo correto (http/https)
- `X-Forwarded-Host $server_name` - garante host correto
- Headers adicionais para melhor compatibilidade

### 3. Frontend (✅ Já Compatível)
Seu `frontend/app.js` já usa URLs relativas (`/api/...`), então funcionará corretamente.

## Passos para Implementar

1. **Reinicie o Flask:**
   ```bash
   # Se estiver rodando em um terminal
   # Ctrl+C para parar
   # Depois rode novamente
   python main.py --port 5000 --host 0.0.0.0
   ```

2. **Atualize a configuração do nginx:**
   - Copie o conteúdo de `nginx-config.conf` para seu arquivo nginx
   - Ou se já tem um arquivo, substitua o bloco `location /skedway/`

3. **Teste a configuração do nginx:**
   ```bash
   sudo nginx -t
   ```

4. **Recarregue o nginx:**
   ```bash
   sudo systemctl reload nginx
   # ou
   sudo service nginx reload
   ```

5. **Teste a aplicação:**
   - Acesse `cassiorodrigues.tech/skedway/`
   - Abra o Console do Navegador (F12) e veja se há erros
   - Teste as funcionalidades (carregar contas, agendar execuções, etc.)

## Debug
Se ainda tiver problemas, verifique:

1. **Logs do Flask:**
   ```bash
   # Sua aplicação já registra logs, veja a saída do terminal
   ```

2. **Logs do Nginx:**
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

3. **Console do Navegador:**
   - Abra F12 > Console
   - Procure por erros de rede ou CORS

4. **Teste direto (bypass nginx):**
   ```bash
   curl http://127.0.0.1:5000/api/accounts
   ```
   Se funcionar, o problema é nginx. Se não funcionar, é o Flask.

## Checkpoints Importantes
- ✅ Flask atualizado com ProxyFix
- ⚠️ Nginx configurado com headers corretos
- ✅ Frontend usa URLs relativas
- ⚠️ Nginx recarregado tem ser feito
- ⚠️ Flask reiniciado após código mudo
