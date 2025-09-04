# Enhanced Logging System Configuration

## 🎯 **Overview**

The enhanced MCP server includes comprehensive logging to track both workflow progression and data source usage. This helps you understand whether you're getting live API data or fallback mock data.

## 📊 **Two Log Types**

### 1. Workflow Log (`logs/workflow.log`)
- **Purpose**: Tracks workflow step progression, timing, success/failure
- **Format**: `🔄 WORKFLOW | 🚀 Company Profile [AAPL] - STARTED`
- **Shows**: Step names, duration, completion status, error details

### 2. Data Sources Log (`logs/data_sources.log`) 
- **Purpose**: Tracks API calls, data sources, mock vs live data
- **Format**: `📊 DATA | ✅ 🟢 LIVE | quote [AAPL] | Response time: 0.45s`
- **Shows**: Data source type, endpoint, success/failure, timing

## 🔧 **Configuration Options**

### Environment Variables

```bash
# Log level control
export MCP_LOG_LEVEL="INFO"          # DEBUG, INFO, WARN, ERROR

# Enable/disable logging types  
export MCP_ENABLE_WORKFLOW_LOG="true"   # true/false
export MCP_ENABLE_DATA_LOG="true"       # true/false
```

### Log Location
- **Directory**: `/Users/akash/Documents/WORK/MCProject/logs/`
- **Files**: `workflow.log`, `data_sources.log`
- **Auto-created**: Directory and files created automatically

## 🎨 **Visual Indicators**

### Data Source Types
- 🟢 **LIVE** - Real API data (Finnhub, SEC Edgar)
- 🟡 **MOCK** - Mock/test data (when API keys missing)
- 🔵 **LIVE** - SEC Edgar live data
- 🟠 **MOCK** - SEC Edgar mock data  
- 🟣 **CALC** - Calculated/algorithmic data (sentiment analysis)
- ⚫ **N/A** - Data unavailable

### Workflow Status
- 🚀 **STARTED** - Workflow step beginning
- ✅ **COMPLETED** - Step finished successfully
- ❌ **FAILED** - Step failed with error
- ⚠️ **FALLBACK** - Using fallback/mock data

### API Call Status
- ✅ **SUCCESS** - API call succeeded
- ❌ **FAILED** - API call failed
- 🔄 **MOCK** - Using mock data
- ⚠️ **FALLBACK** - Fell back to alternative source

## 📈 **Data Quality Tracking**

### Summary Logging
```
📈 SUMMARY [AAPL] | Total: 8 | Live: 6 (75%) | Mock: 2 (25%) | Failed: 0
```

### What This Shows:
- **Total calls**: All API/data requests made
- **Live percentage**: How much real API data was used
- **Mock percentage**: How much fallback data was used  
- **Failed calls**: Number of API failures

## 🔍 **Example Log Outputs**

### Workflow Log Example
```
09:15:23 | 🔄 WORKFLOW | INFO | 🚀 Company Profile [AAPL] - STARTED
09:15:24 | 🔄 WORKFLOW | INFO | ✅ Company Profile [AAPL] - COMPLETED (0.82s) | Market cap: 3500000
09:15:24 | 🔄 WORKFLOW | INFO | 🚀 News Analysis [AAPL] - STARTED  
09:15:25 | 🔄 WORKFLOW | INFO | ✅ News Analysis [AAPL] - COMPLETED (1.15s) | 147 articles processed
```

### Data Sources Log Example  
```
09:15:23 | 📊 DATA | INFO | ✅ 🟢 LIVE | stock/profile2 [AAPL] | Response time: 0.45s
09:15:24 | 📊 DATA | INFO | ✅ 🟢 LIVE | quote [AAPL] | Response time: 0.37s
09:15:24 | 📊 DATA | INFO | ✅ 🟢 LIVE | company-news [AAPL] | Response time: 1.02s
09:15:25 | 📊 DATA | WARN | ⚠️ 🟠 MOCK | recent_filings [AAPL] | SEC Edgar not configured, using mock data
09:15:26 | 📊 DATA | INFO | ✅ 🟣 CALC | sentiment_analysis [AAPL] | 147 articles analyzed, sentiment ratio: 0.65
09:15:27 | 📊 DATA | WARN | 📈 SUMMARY [AAPL] | Total: 8 | Live: 6 (75%) | Mock: 2 (25%) | Failed: 0
```

## 🎯 **Key Benefits**

### 1. **Data Source Transparency**
- Always know if you're getting real or mock data
- See exactly which APIs are working vs failing
- Track API response times and performance

### 2. **Workflow Monitoring**  
- Monitor step-by-step workflow progression
- See timing for each analysis step
- Get detailed error information when things fail

### 3. **Quality Assurance**
- Data completeness percentages
- Source attribution for audit trails  
- Performance metrics for optimization

### 4. **Debugging Support**
- Clear error messages with context
- Timing information for performance issues
- Fallback detection for configuration problems

## 🚀 **Using the Logs**

### For Development
```bash
# Watch logs in real-time
tail -f /Users/akash/Documents/WORK/MCProject/logs/workflow.log
tail -f /Users/akash/Documents/WORK/MCProject/logs/data_sources.log
```

### For Analysis
- Check `data_sources.log` to verify API connectivity
- Check `workflow.log` to diagnose workflow issues  
- Look for 🟡 MOCK or 🟠 MOCK indicators to spot fallback usage
- Monitor response times to identify performance bottlenecks

### For Production Monitoring
- Set up log rotation for the log files
- Monitor for high failure rates or mock data usage
- Alert on workflow failures or long response times
- Track data quality percentages over time