# API Examples

Exemplos de como usar a API do Execution Dashboard.

## Base URL

```
http://localhost:5000
```

## Endpoints

### 1. Listar Todas as Execuções

**Endpoint**: `GET /api/executions`

**Descrição**: Retorna uma lista de todas as execuções

**Exemplo de Requisição**:

```bash
curl http://localhost:5000/api/executions
```

**Exemplo de Resposta**:

```json
[
  {
    "execution_time": "2026-04-05T15:34:59.888493",
    "target_date": "2026-04-12",
    "desks_attempted": ["81502"],
    "result": "dry_run_success",
    "booked_desk": "81502",
    "duration_seconds": 76.7,
    "screenshots": 7,
    "screenshot_files": [
      "01_login_page.png",
      "02_email_filled.png",
      "03_password_step.png",
      "04_password_filled.png",
      "05_after_login.png",
      "06_booking_page_81502.png",
      "07_before_submit_81502.png"
    ],
    "timestamp": "2026-04-05_153459"
  },
  {
    "execution_time": "2026-04-05T15:31:13.293917",
    "target_date": "N/A",
    "desks_attempted": [],
    "result": "login_failed",
    "booked_desk": null,
    "duration_seconds": 72.08,
    "screenshots": 4,
    "screenshot_files": [
      "01_login_page.png",
      "02_error_no_password_field.png",
      "03_login_page.png",
      "04_error_no_password_field.png"
    ],
    "timestamp": "2026-04-05_153113"
  }
]
```

### 2. Obter Detalhes de uma Execução Específica

**Endpoint**: `GET /api/executions/<timestamp>`

**Parametros**:
- `timestamp` (string) - Timestamp da execução no formato `YYYY-MM-DD_HHMMSS`

**Descrição**: Retorna dados completos de uma execução, incluindo logs

**Exemplo de Requisição**:

```bash
curl http://localhost:5000/api/executions/2026-04-05_153459
```

**Exemplo de Resposta**:

```json
{
  "execution_time": "2026-04-05T15:34:59.888493",
  "target_date": "2026-04-12",
  "desks_attempted": ["81502"],
  "result": "dry_run_success",
  "booked_desk": "81502",
  "duration_seconds": 76.7,
  "screenshots": 7,
  "screenshot_files": [
    "01_login_page.png",
    "02_email_filled.png",
    "03_password_step.png",
    "04_password_filled.png",
    "05_after_login.png",
    "06_booking_page_81502.png",
    "07_before_submit_81502.png"
  ],
  "execution_log": "[2026-04-05 15:34:59] [INFO    ] [logger      ] Execution started…\n[2026-04-05 15:34:59] [INFO    ] [logger      ] Validating credentials…\n…"
}
```

### 3. Download de Screenshot

**Endpoint**: `GET /api/executions/<timestamp>/screenshots/<filename>`

**Parametros**:
- `timestamp` (string) - Timestamp da execução
- `filename` (string) - Nome do arquivo PNG/JPG

**Descrição**: Retorna a imagem do screenshot

**Exemplo de Requisição**:

```bash
curl http://localhost:5000/api/executions/2026-04-05_153459/screenshots/01_login_page.png -o login_page.png
```

### 4. Verificação de Saúde

**Endpoint**: `GET /api/health`

**Descrição**: Verifica se o servidor está funcionando

**Exemplo de Requisição**:

```bash
curl http://localhost:5000/api/health
```

**Exemplo de Resposta**:

```json
{
  "status": "ok",
  "logs_dir": "/path/to/logs",
  "logs_dir_exists": true
}
```

## Exemplos em Diferentes Linguagens

### JavaScript (Fetch API)

```javascript
// Listar execuções
fetch('http://localhost:5000/api/executions')
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error('Error:', error));

// Obter detalhes de uma execução
fetch('http://localhost:5000/api/executions/2026-04-05_153459')
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error('Error:', error));
```

### Python

```python
import requests

# Listar execuções
response = requests.get('http://localhost:5000/api/executions')
executions = response.json()
print(executions)

# Obter detalhes
response = requests.get('http://localhost:5000/api/executions/2026-04-05_153459')
details = response.json()
print(details)

# Download de screenshot
response = requests.get(
    'http://localhost:5000/api/executions/2026-04-05_153459/screenshots/01_login_page.png'
)
with open('screenshot.png', 'wb') as f:
    f.write(response.content)
```

### cURL

```bash
# Listar execuções
curl -X GET http://localhost:5000/api/executions | jq

# Obter detalhes com pretty print
curl -X GET http://localhost:5000/api/executions/2026-04-05_153459 | jq

# Download com curl
curl -o screenshot.png http://localhost:5000/api/executions/2026-04-05_153459/screenshots/01_login_page.png

# Salvando com timestamp no nome
curl -o $(date +%Y%m%d_%H%M%S).png http://localhost:5000/api/executions/2026-04-05_153459/screenshots/01_login_page.png
```

### Axios (Node.js/JavaScript)

```javascript
const axios = require('axios');

// Listar execuções
axios.get('http://localhost:5000/api/executions')
  .then(res => console.log(res.data))
  .catch(err => console.error(err));

// Obter detalhes
axios.get('http://localhost:5000/api/executions/2026-04-05_153459')
  .then(res => console.log(res.data))
  .catch(err => console.error(err));

// Download de arquivo
axios.get('http://localhost:5000/api/executions/2026-04-05_153459/screenshots/01_login_page.png', {
  responseType: 'arraybuffer'
}).then(res => {
  const fs = require('fs');
  fs.writeFileSync('screenshot.png', res.data);
});
```

## Filtros e Processamento

### Filtrar por Resultado de Sucesso

```javascript
// JavaScript
fetch('http://localhost:5000/api/executions')
  .then(r => r.json())
  .then(executions => {
    const successes = executions.filter(e => 
      e.result === 'dry_run_success' || e.result === 'success'
    );
    console.log('Execuções com Sucesso:', successes);
  });
```

### Filtrar por resultado de Falha

```javascript
// JavaScript
fetch('http://localhost:5000/api/executions')
  .then(r => r.json())
  .then(executions => {
    const failures = executions.filter(e => 
      e.result === 'login_failed' || e.result === 'booking_failed'
    );
    console.log('Execuções com Falha:', failures);
  });
```

### Estatísticas

```javascript
// JavaScript
fetch('http://localhost:5000/api/executions')
  .then(r => r.json())
  .then(executions => {
    const stats = {
      total: executions.length,
      success: executions.filter(e => 
        ['dry_run_success', 'success'].includes(e.result)
      ).length,
      failed: executions.filter(e => 
        ['login_failed', 'booking_failed', 'error'].includes(e.result)
      ).length,
      average_duration: (
        executions.reduce((sum, e) => sum + e.duration_seconds, 0) / executions.length
      ).toFixed(2),
      total_screenshots: executions.reduce((sum, e) => sum + e.screenshots, 0)
    };
    console.log('Estatísticas:', stats);
  });
```

## HTTP Status Codes

| Código | Significado |
|--------|-------------|
| 200 | OK - Requisição bem-sucedida |
| 404 | Not Found - Recurso não encontrado |
| 500 | Internal Server Error - Erro no servidor |

## Rate Limiting

Não há rate limiting implementado. Use com responsabilidade em ambientes de produção.

## CORS

CORS está habilitado para todas as origens. Em produção, configure para apenas as origens necessárias.

## Paginação

Não há paginação neste momento. Todas as execuções são retornadas em uma única requisição.

## Dicas de Performance

1. **Caching**: Cache os resultados de execuções no cliente
2. **Lazy Loading**: Carregue os detalhes de execuções apenas quando necessário
3. **Compressão**: Use gzip quando tiver muitas execuções
4. **Resumo**: Para listas grandes, carregue apenas os campos necessários

## Contato & Suporte

Para problemas ou sugestões, verifique o README.md principal.
