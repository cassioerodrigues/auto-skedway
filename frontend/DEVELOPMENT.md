# Frontend Development Guide

## Overview

Este é um frontend vanilla (sem frameworks) para o Execution Dashboard. O objetivo foi criar uma interface moderna e responsiva usando apenas HTML, CSS e JavaScript, com Flask como backend.

## Stack

- **Frontend**: HTML5, CSS3, Vanilla JavaScript (ES6+)
- **Backend**: Flask, Python 3.8+
- **Design**: Dark theme, Glass morphism, Responsive grid layouts
- **Tools**: No build step required (serve directly)

## Project Structure

```
frontend/
├── api.py              # Flask backend
├── index.html          # Single HTML page
├── styles.css          # All CSS styling
├── app.js              # Vanilla JS logic
├── start-server.bat    # Windows startup script
├── start-server.sh     # Linux/Mac startup script
├── README.md           # User documentation
├── API_EXAMPLES.md     # API usage examples
└── DEVELOPMENT.md      # This file
```

## Architecture

### Frontend (HTML/CSS/JS)

```
User Interface (index.html)
    ↓
Event Listeners (app.js)
    ↓
Fetch API Calls
    ↓
Server (api.py)
    ↓
File System (logs/)
```

### Backend (Flask)

```
Flask App (api.py)
    ├── Static Files Route (/)
    ├── API Routes (/api/*)
    ├── Helper Functions
    └── Error Handlers
```

## Development Workflow

### 1. Running Locally

```bash
cd frontend
python api.py
```

Then open `http://localhost:5000` in your browser.

### 2. Making Changes

#### CSS Changes
- Edit `styles.css`
- Refresh browser (no build step needed)
- CSS uses CSS custom properties for theming

#### JavaScript Changes
- Edit `app.js`
- Refresh browser
- Uses Fetch API for all HTTP requests
- Pure vanilla JavaScript (no dependencies)

#### Backend Changes
- Edit `api.py`
- Server reloads automatically (debug mode)
- Test with `/api/health` endpoint

#### HTML Changes
- Edit `index.html`
- Refresh browser
- Try to minimize changes (mostly static)

### 3. Testing

#### Manual Testing
1. Navigate to `http://localhost:5000`
2. Check console (F12 → Console) for errors
3. Test sorting, filtering, modal interactions
4. Test screenshot modal

#### API Testing
```bash
# List executions
curl http://localhost:5000/api/executions | jq

# Get specific execution
curl http://localhost:5000/api/executions/2026-04-05_153459 | jq

# Health check
curl http://localhost:5000/api/health
```

## CSS Architecture

### Variables (`:root`)
All colors, spacing, and transitions defined as CSS variables for consistency:

```css
--color-brand: #8251EE
--spacing-md: 1rem
--radius-lg: 0.75rem
```

### BEM Naming
Uses Block-Element-Modifier pattern:

```css
.execution-card {}              /* Block */
.execution-card__header {}      /* Element */
.execution-card--loading {}     /* Modifier */
```

### Responsive Design
Mobile-first approach with breakpoints:

```css
/* Default: Mobile */
.stats-grid { grid-template-columns: repeat(2, 1fr); }

/* Tablet */
@media (max-width: 768px) { }

/* Desktop */
@media (max-width: 480px) { }
```

## JavaScript Architecture

### State Management
Single state object:

```javascript
const state = {
  executions: [],
  sortOrder: 'newest',
  selectedExecution: null,
};
```

### DOM References
Cached selectors:

```javascript
const elements = {
  refreshBtn: document.getElementById('refreshBtn'),
  executionsList: document.getElementById('executionsList'),
  // ...
};
```

### Async Patterns
All API calls use async/await:

```javascript
async function fetchExecutions() {
  try {
    const response = await fetch('/api/executions');
    return await response.json();
  } catch (error) {
    console.error('Error:', error);
  }
}
```

### Event Delegation
Listeners attached to documents and event handlers on elements:

```javascript
card.addEventListener('click', () => showExecutionDetails(execution));
```

## Adding New Features

### 1. New Statistic Card

In `index.html`, add to `.stats-grid`:
```html
<div class="stat-card">
  <div class="stat-card__label">New Stat</div>
  <div class="stat-card__value" id="newStat">-</div>
</div>
```

In `app.js`, update `updateStats()`:
```javascript
const newValue = executions.filter(...).length;
elements.newStat.textContent = newValue;
```

### 2. New API Endpoint

In `api.py`:
```python
@app.route("/api/new-endpoint", methods=["GET"])
def new_endpoint():
    try:
        # Logic here
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500
```

In `app.js`:
```javascript
async function fetchNewData() {
  const response = await fetch('/api/new-endpoint');
  return await response.json();
}
```

### 3. New Filter

In `index.html`, add select:
```html
<select id="statusFilter" class="sort-select">
  <option value="all">Todos</option>
  <option value="success">Sucesso</option>
  <option value="failed">Falha</option>
</select>
```

In `app.js`:
```javascript
elements.statusFilter.addEventListener('change', (e) => {
  state.filterStatus = e.target.value;
  renderExecutions(state.executions);
});

function filterExecutions(executions) {
  if (state.filterStatus === 'all') return executions;
  // Filter logic
}
```

## Performance Optimization Tips

1. **Lazy Load Screenshots**
   - Only load when modal opens
   - Current implementation uses `loading="lazy"`

2. **Pagination**
   - For >100 executions, implement pagination
   - Add API limit/offset parameters

3. **Caching**
   - Cache execution list in localStorage
   - Invalidate on refresh

4. **Virtual Scrolling**
   - If 1000+ executions, implement virtual scroll

## Common Issues & Solutions

### Issue: Port already in use
```python
# In api.py, change port:
app.run(host="0.0.0.0", port=5001)
```

### Issue: Logs not loading
- Check logs folder exists: `Path(__file__).parent.parent / "logs"`
- Check summary.json files exist
- Check Flask logs for path errors

### Issue: Screenshots 404
- Verify PNG/JPG files exist in execution folders
- Check filename spelling matches
- Check file permissions

### Issue: CORS errors
- Flask-CORS is enabled for all origins
- If still issues, try opening in same origin

### Issue: Modal not closing
- Check JavaScript console for errors
- Verify backdrop event listener attached
- Check CSS z-index stacking

## Code Style Guidelines

### CSS
- Use lowercase, hyphenated class names
- BEM pattern for components
- CSS variables for reusable values
- Group related rules
- Include comments for sections

### JavaScript
- Use descriptive function names
- Add JSDoc comments for complex functions
- Use const/let over var
- Avoid deep nesting
- Error handling in all API calls

### HTML
- Semantic HTML5 elements
- Data attributes for JS hooks
- Accessible ARIA labels where needed
- Mobile-first structure

## Debugging

### Browser DevTools
1. **Console**: Check for JavaScript errors
2. **Network**: Monitor API calls
3. **Elements**: Inspect CSS and DOM
4. **Sources**: Debug JavaScript

### Flask Logging
Set environment:
```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
```

### Adding Debug Output
```javascript
console.log('State:', state);
console.log('Executions:', state.executions);
```

## Deployment Checklist

- [ ] Test all features locally
- [ ] No console errors
- [ ] All screenshots load
- [ ] Modal works on mobile
- [ ] API health check passes
- [ ] Update `README.md` if features changed
- [ ] No hardcoded paths (use relative)
- [ ] Error handling for missing logs folder

## Future Improvements

1. **Search & Filter**
   - Full-text search
   - Filter by status, date range
   - Filter by desk number

2. **Dashboard Widgets**
   - Success rate chart
   - Duration trend graph
   - Most booked desks
   - Time series of executions

3. **Animations**
   - Page transitions
   - Loading skeletons
   - Scroll animations
   - Stagger animations for lists

4. **Dark/Light Mode**
   - Toggle in header
   - Persist preference to localStorage
   - Smooth color transitions

5. **Export/Reporting**
   - Export execution list as CSV
   - Generate summary reports
   - Compare two executions

6. **Advanced Features**
   - Execution scheduling UI
   - Retry failed executions
   - Webhook notifications
   - Execution timeline view

## Resources

- [MDN - Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API)
- [CSS Grid Guide](https://css-tricks.com/snippets/css/complete-guide-grid/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Async/Await Guide](https://javascript.info/async-await)

## Contributing

1. Create a branch: `git checkout -b feature/your-feature`
2. Make changes and test locally
3. Commit with descriptive messages
4. Push and create pull request
5. Follow code style guidelines

## Questions?

Check:
1. `README.md` - Usage instructions
2. `API_EXAMPLES.md` - API documentation
3. Browser console - Error messages
4. Flask logs - Server errors

---

Last Updated: April 5, 2026
