#!/usr/bin/env python3
"""
SDLC Agent Pipeline - Demo Runner (ROBUST INTERRUPT HANDLING)
Handles both exception-raising and state-returning interrupt behaviors.
"""

import sys
from typing import Optional, Any, Dict
from orchestrator.graph import get_pipeline, build_pipeline
from orchestrator.graph.state import GraphState

# CRITICAL IMPORT: Command is required to resume an interrupted graph
from langgraph.types import Command 


def print_section(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def print_artifact(name: str, artifact: Optional[dict]):
    if artifact:
        print(f"  ✓ {name}")
        if isinstance(artifact, dict):
            for key, value in artifact.items():
                if isinstance(value, (str, int, float, bool)):
                    print(f"      {key}: {value}")
                elif isinstance(value, list):
                    print(f"      {key}: [{len(value)} items]")
                elif isinstance(value, dict):
                    print(f"      {key}: {{...}}")
    else:
        print(f"  ✗ {name} (not generated)")


def run_demo_pipeline():
    print("\n" + "="*70)
    print("  SDLC AGENT SYSTEM - PHASE 1 DEMO (ROBUST INTERRUPT HANDLING)")
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
                
                # CHECK 1: LangGraph returned state with '__interrupt__' key (no exception raised)
                if isinstance(result, dict) and "__interrupt__" in result:
                    print("[Iteration] ⚠️ Pipeline returned state with '__interrupt__' key.")
                    interrupt_val = result.get("__interrupt__")
                    gate_name = "unknown"
                    
                    # LangGraph stores interrupts as a tuple/list of Interrupt objects
                    if isinstance(interrupt_val, (list, tuple)) and len(interrupt_val) > 0:
                        first_interrupt = interrupt_val[0]
                        val = getattr(first_interrupt, 'value', first_interrupt)
                        if isinstance(val, dict):
                            gate_name = val.get('gate', 'unknown')
                    
                    print(f"  ⏸ Pipeline paused at gate: {gate_name}")
                    print("  → Auto-approving for demo purposes...\n")
                    
                    # 🚨 CRITICAL FIX: Use Command(resume=...) to resume the graph
                    current_input = Command(resume="approved")
                    continue
                
                # If no interrupt, it completed successfully
                print("[Iteration] ✅ Pipeline completed successfully without interrupt.")
                break
                
            except Exception as e:
                exc_name = type(e).__name__
                
                # CHECK 2: LangGraph raised an interrupt exception
                if "interrupt" in exc_name.lower() or "Interrupt" in str(type(e)):
                    gate_info = getattr(e, 'value', {})
                    gate_name = "unknown"
                    
                    if isinstance(gate_info, dict):
                        gate_name = gate_info.get('gate', 'unknown')
                    elif isinstance(gate_info, (list, tuple)) and len(gate_info) > 0:
                        first_interrupt = gate_info[0]
                        val = getattr(first_interrupt, 'value', first_interrupt)
                        if isinstance(val, dict):
                            gate_name = val.get('gate', 'unknown')
                            
                    print(f"[Iteration] ⏸ Caught interrupt exception: {exc_name}")
                    print(f"  ⏸ Pipeline paused at gate: {gate_name}")
                    print("  → Auto-approving for demo purposes...\n")
                    
                    # 🚨 CRITICAL FIX: Use Command(resume=...) to resume the graph
                    current_input = Command(resume="approved")
                else:
                    print(f"[Iteration] 🔴 UNEXPECTED ERROR: {exc_name}")
                    import traceback
                    traceback.print_exc()
                    return False
        else:
            print("\n⚠️ Warning: Max iterations reached. Pipeline may be stuck.")
        
        if result is None:
            print("✗ Pipeline did not complete.")
            return False
            
        print("\n" + "="*70)
        print("  EXECUTION COMPLETE")
        print("="*70)
        
        print(f"\n🔍 FINAL STATE KEYS: {list(result.keys())}")
        
        print("\nGenerated Artifacts:")
        for key in ["spec_json", "design_doc", "code_artifact", "review_report", "test_report", "build_report", "deployment_report", "ops_report"]:
            if key in result and result[key]:
                print(f"  ✓ {key}")
            else:
                print(f"  ✗ {key} (MISSING)")
                
        print("\n" + "="*70)
        print("  PHASE 1 COMPLETE ✓")
        print("="*70)
        print("\nThe foundation is ready. You can now:")
        print("  • Start Phase 2: Build real agents with LLM calls")
        print("  • Run tests: pytest tests/test_pipeline_e2e.py -v")
        print("  • Check LangSmith traces (if configured)")
        print("="*70 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n🔴 FATAL ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_demo_pipeline()
    sys.exit(0 if success else 1)