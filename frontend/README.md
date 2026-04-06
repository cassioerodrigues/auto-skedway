# 🚀 Execution Dashboard

Um dashboard moderno e responsivo para visualizar execuções do Auto Skedway com design dark theme estético e funcionalidades completas.

## ✨ Características

- 📊 **Visualização de Execuções** - Lista de todas as execuções realizadas com status e detalhes
- 🖼️ **Galeria de Screenshots** - Visualize todas as capturas de tela das execuções
- 📝 **Logs Detalhados** - Acesse o execution log completo de cada execução
- 📋 **JSON Summary** - Veja o arquivo summary.json de cada execução
- 🎨 **Design Moderno** - Dark theme com glass morphism effects
- 📱 **Responsivo** - Funciona perfeitamente em desktop, tablet e mobile
- ⚡ **Sem Dependências Frontend** - HTML, CSS e JavaScript vanilla (sem frameworks)
- 🔄 **Atualização em Tempo Real** - Botão de refresh para carregar novas execuções

## 🛠️ Requisitos

- Python 3.8+
- Flask 2.3.0+
- Flask-CORS 4.0.0+

As dependências estão incluídas em `requirements.txt` no diretório pai.

## 🚀 Instalação

1. **Instale as dependências** (se ainda não instalou):
   ```bash
   pip install -r ../requirements.txt
   ```

2. **Navegue até a pasta frontend**:
   ```bash
   cd frontend
   ```

## 📖 Como Usar

### Iniciar o servidor

```bash
python api.py
```

Ou usando Python diretamente:

```bash
python3 api.py
```

O servidor será iniciado em `http://localhost:5000`

### Acessar o Dashboard

Abra seu navegador e acesse:
- **Local**: http://localhost:5000
- **Na rede**: http://seu-ip:5000

## 📁 Estrutura de Arquivos

```
frontend/
├── api.py              # Backend Flask - fornece API para os dados
├── index.html          # Página HTML principal
├── styles.css          # Estilos CSS (dark theme + glass morphism)
├── app.js              # JavaScript vanilla - lógica do dashboard
└── README.md           # Este arquivo
```

## 🎯 Funcionalidades

### Lista de Execuções
- Visualize todas as execuções ordenadas por data
- Veja o status de cada execução (sucesso/falha)
- Informações rápidas: data alvo, mesa agendada, duração, screenshots

### Detalhes da Execução
Clique em qualquer execução para ver:

1. **Resumo** - Informações gerais da execução
   - Resultado (sucesso/falha)
   - Data alvo
   - Mesa agendada
   - Mesas tentadas
   - Duração
   - Timestamp completo

2. **Galeria de Screenshots** - Todas as imagens capturadas
   - Clique para visualizar em tela cheia
   - Tooltips com nome do arquivo
   - Navegação responsiva

3. **Execution Log** - Log completo da execução
   - Collapsível (mostrar/ocultar)
   - Formatação de monospace
   - Scroll independente para logs longos

4. **Summary JSON** - Dados estruturados em JSON
   - Collapsível (mostrar/ocultar)
   - Formatação com indentação
   - Fácil de copiar

## 🎨 Design & UX

### Paleta de Cores
- **Fundo Principal**: Dark neutral (HSL 240, 6%, 10%)
- **Marca**: Purple (#8251EE)
- **Texto**: Branco puro com variações de opacidade
- **Status**: Verde (sucesso), Vermelho (erro), Amarelo (aviso)

### Efeitos Visuais
- Glass morphism com backdrop blur
- Transições suaves em hover
- Animações de fade-in ao carregar
- Ícones SVG inline
- Scroll suave

### Responsive Design
- **Desktop**: Layout em grid multi-coluna
- **Tablet**: 2x2 grid para stats, screenshots em 3 colunas
- **Mobile**: Layout em coluna única, screenshots em 2 colunas

## 🔌 API Endpoints

### Public Endpoints

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/` | GET | Página principal |
| `/api/executions` | GET | Lista todas as execuções |
| `/api/executions/<timestamp>` | GET | Detalhes de uma execução específica |
| `/api/executions/<timestamp>/screenshots/<filename>` | GET | Download de screenshot |
| `/api/health` | GET | Verificação de saúde do servidor |

### Exemplo de Resposta - Lista de Execuções

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
    "screenshot_files": ["01_login_page.png", ...],
    "timestamp": "2026-04-05_153459"
  }
]
```

## 🐛 Troubleshooting

### Porta já em uso
Se a porta 5000 já estiver em uso, você pode modificar o arquivo `api.py`:

```python
app.run(host="0.0.0.0", port=5001)  # Mude para outra porta
```

### Logs não aparecem
- Verifique se a pasta `logs` existe no diretório raiz do projeto
- Certifique-se de que os arquivos `summary.json` existem nas subpastas

### Screenshots não carregam
- Verifique se os arquivos PNG/JPG existem nas pastas de execução
- Confirme as permissões de leitura dos arquivos

### CORS errors
- Os erros CORS foram resolvidos com Flask-CORS
- Se ainda houver problemas, verifique a URL do servidor

## 📊 Performance

- **Carregamento Inicial**: Todos os dados carregam de uma vez
- **Lazy Loading**: Screenshots carregam sob demanda
- **Filtros**: Ordenação em tempo real sem recarregar do servidor
- **Modal**: Detalhes carregam apenas ao clicar

## 🔐 Segurança

- Validação de paths - previne directory traversal
- Validação de tipos de arquivo para screenshots
- CORS configurado apropriadamente
- Sem exposição de dados sensíveis

## 📝 Logs & Debug

O servidor exibe logs de:
- Inicialização
- Carregamento de execuções
- Erros de leitura de arquivos
- Requisições HTTP

Todos os logs incluem timestamp e nível de severidade.

## 🚀 Próximas Melhorias Sugeridas

- [ ] Busca por timestamp ou resultado
- [ ] Filtro por data range
- [ ] Estatísticas por período
- [ ] Exportação de dados (CSV/PDF)
- [ ] Dark/Light mode toggle
- [ ] Comparação entre execuções
- [ ] Gráficos de tendências
- [ ] Notificações em tempo real

## 📄 Licença

Parte do projeto Auto Skedway.

## 👤 Desenvolvimento

Desenvolvido para o Auto Skedway - Automação de agendamento de mesas Volvo Skedway.
