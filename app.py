import argparse
import sys
from ui.app import create_app

def main():
    parser = argparse.ArgumentParser(description="Dubai Real Estate Leads Qualification Dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Host address to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5001, help="Port to bind (default: 5001)")
    parser.add_argument("--debug", action="store_true", help="Run Flask in debug mode")
    parser.add_argument("--results-dir", default="results", help="Directory containing pipeline results (default: results)")
    parser.add_argument("--input-dir", default="input", help="Directory containing raw inputs (default: input)")
    args = parser.parse_args()

    app = create_app(results_dir=args.results_dir, input_dir=args.input_dir)
    print("=" * 70)
    print("DUBAI REAL ESTATE LEADS QUALIFICATION DASHBOARD")
    print(f"Results Directory: {args.results_dir}")
    print(f"Input Directory:   {args.input_dir}")
    print(f"Dashboard URL:     http://{args.host}:{args.port}")
    print("=" * 70)
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()
