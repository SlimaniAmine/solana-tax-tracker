# Crypto Tax Tracker

An open‑source crypto tax automation tool that aggregates Solana staking rewards, exchange transactions, and historical price data to generate accurate, audit‑ready tax reports for multiple countries.

## Features

- **Multi-Wallet Support**: Process up to 10 Solana wallet addresses
- **CEX Integration**: Connect to Kraken, Coinbase, and other exchanges via API or CSV upload
- **Country-Specific Tax Rules**: Modular tax calculation engines (starting with Germany)
- **Historical Price Data**: Automatic fetching of historical token prices
- **Currency Conversion**: USD to EUR (and other currencies) conversion
- **Excel Export**: Generate detailed tax reports in Excel format
- **Audit Trail**: Complete transparency in tax calculations

## Architecture

- **Backend**: Python 3.11+ with FastAPI
- **Frontend**: React 18+ with TypeScript and Vite
- **Styling**: Tailwind CSS

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- npm or yarn

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`

### Docker Setup

```bash
docker-compose up
```

## Configuration

Copy `.env.example` to `.env` and configure:

- `SOLANA_RPC_URL`: Solana RPC endpoint
- `COINGECKO_API_KEY`: Optional API key for higher rate limits
- `EXCHANGE_RATE_API_KEY`: For currency conversion

## Development Status

All core phases have been implemented:

- ✅ Phase 1: Foundation - Project structure, FastAPI, React setup
- ✅ Phase 2: Solana Integration - Chain adapter, transaction fetching and parsing
- ✅ Phase 3: Price & Currency Services - CoinGecko API, currency conversion, caching
- ✅ Phase 4: Transaction Normalization - Multi-wallet merging, year filtering, price enrichment
- ✅ Phase 5: German Tax Rules - Tax calculation engine with FIFO, holding period rules
- ✅ Phase 6: CEX Integration - Kraken and Coinbase CSV parsers, API structure
- ✅ Phase 7: Frontend UI - Complete UI with all components, wallet inputs, results display
- ✅ Phase 8: Reporting & Export - Excel export, audit trail, detailed breakdowns
- ✅ Phase 9: Polish & Testing - Error handling, integration, code quality

## Known Limitations

- CEX API integration (Kraken/Coinbase) is structured but not fully implemented - CSV upload works
- Some advanced Solana transaction types may need additional parsing logic
- Price data depends on CoinGecko API availability and rate limits

## License

MIT License
