#!/usr/bin/env python3
"""
SDLC Agent Pipeline - Demo Runner (MAXIMUM DEBUG)
"""

import sys
from typing import Optional, Any, Dict
from orchestrator.graph import get_pipeline, build_pipeline
from orchestrator.graph.state import GraphState


def run_demo_pipeline():
    print("\n" + "="*70)
    print("  SDLC AGENT SYSTEM - PHASE 1 DEMO (MAXIMUM DEBUG)")
    print("="*70 + "\n")
    
    print("Building pipeline with MemorySaver (dev mode)...")
    pipeline = build_pipeline(use_postgres=False)
    print("✓ Pipeline compiled successfully\n")
    
    initial_state: GraphState = {
        "project_id": "demo-project-001",
        "run_id": "demo-run-001",
        "input_data": {"type": "prd_text", "content": "Build a REST API for a todo application."},
        "mode": "full_pipeline",
        "retry_count": 0,
    }
    
    config = {"configurable": {"thread_id": "demo-thread-001"}}
    
    print("="*70)
    print("  STARTING PIPELINE EXECUTION")
    print("="*70)
    
    try:
        current_input = initial_state
        max_iterations = 10
        result = None
        
        for iteration in range(max_iterations):
            print(f"\n[Iteration {iteration+1}] Invoking pipeline...")
            try:
                result = pipeline.invoke(current_input, config=config)
                print("[Iteration] ✅ Pipeline.invoke() returned WITHOUT raising GraphInterrupt.")
                break
                
            except Exception as e:
                exc_name = type(e).__name__
                print(f"[Iteration] ⚠️ Caught exception: {exc_name}")
                
                if exc_name == "GraphInterrupt" or "interrupt" in str(type(e)).lower():
                    gate_info = getattr(e, 'value', {})
                    gate_name = gate_info.get('gate', 'unknown') if isinstance(gate_info, dict) else 'unknown'
                    print(f"  ⏸ Pipeline paused at gate: {gate_name}")
                    print("  → Auto-approving for demo purposes...\n")
                    current_input = "approved"
                else:
                    print(f"  🔴 UNEXPECTED ERROR: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
        else:
            print("\n⚠️ Warning: Max iterations reached.")
        
        if result is None:
            print("✗ Pipeline did not complete.")
            return False
            
        print("\n" + "="*70)
        print("  EXECUTION COMPLETE")
        print("="*70)
        
        # DEBUG: Print exact keys in the final state
        print(f"\n🔍 FINAL STATE KEYS: {list(result.keys())}")
        
        print("\nGenerated Artifacts:")
        for key in ["spec_json", "design_doc", "code_artifact", "review_report", "test_report", "build_report", "deployment_report", "ops_report"]:
            if key in result and result[key]:
                print(f"  ✓ {key}")
            else:
                print(f"  ✗ {key} (MISSING)")
                
        return True
        
    except Exception as e:
        print(f"\n🔴 FATAL ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_demo_pipeline()
    sys.exit(0 if success else 1)