"""
Phase 2 Evaluation Runner.
Runs the PRD → Review loop across the dataset and measures the acceptance rate.
"""

import sys
import time
import uuid
from typing import Dict, Any

from orchestrator.graph import build_pipeline
from orchestrator.graph.state import GraphState
from langgraph.types import Command

from evals.dataset import PRD_DATASET


def run_single_eval(prd: Dict[str, Any]) -> Dict[str, Any]:
    """Runs the pipeline for a single PRD and returns the results."""
    print(f"\n{'='*60}")
    print(f"Running Eval: {prd['id']} - {prd['name']}")
    print(f"{'='*60}")
    
    # Build a fresh pipeline for each eval to ensure clean state
    pipeline = build_pipeline(use_postgres=False)
    
    thread_id = f"eval-{prd['id']}-{uuid.uuid4().hex[:8]}"
    run_id = str(uuid.uuid4())
    
    initial_state: GraphState = {
        "project_id": prd["id"],
        "run_id": run_id,
        "input_data": {"type": "prd_text", "content": prd["text"]},
        "mode": "full_pipeline",
        "retry_count": 0,
    }
    
    config = {"configurable": {"thread_id": thread_id}}
    
    current_input = initial_state
    result = None
    error_msg = None
    
    try:
        # Execute pipeline, handling interrupts
        for iteration in range(10):
            try:
                result = pipeline.invoke(current_input, config=config)
                
                # Check if pipeline paused at a human gate
                if isinstance(result, dict) and "__interrupt__" in result:
                    current_input = Command(resume="approved")
                    continue
                else:
                    break # Pipeline completed
            except Exception as e:
                error_msg = str(e)
                break
    except Exception as e:
        error_msg = str(e)
        
    # Check if the 4 core Phase 1-4 artifacts were successfully generated
    artifacts_present = {
        "spec_json": bool(result and result.get("spec_json")),
        "design_doc": bool(result and result.get("design_doc")),
        "code_artifact": bool(result and result.get("code_artifact")),
        "review_report": bool(result and result.get("review_report")),
    }
    
    # A "Pass" means all 4 artifacts exist and no fatal error occurred
    passed = all(artifacts_present.values()) and error_msg is None
    
    return {
        "id": prd["id"],
        "name": prd["name"],
        "passed": passed,
        "artifacts": artifacts_present,
        "error": error_msg
    }


def main():
    print("="*60)
    print("  SDLC AGENT - PHASE 2 EVALUATION SUITE")
    print("="*60)
    print(f"Total PRDs to evaluate: {len(PRD_DATASET)}")
    print("Note: This will take ~10-15 minutes on local CPU.\n")
    
    results = []
    start_time = time.time()
    
    for prd in PRD_DATASET:
        res = run_single_eval(prd)
        results.append(res)
        
        status = "✅ PASS" if res["passed"] else "❌ FAIL"
        print(f"\nResult for {res['id']}: {status}")
        if not res["passed"]:
            missing = [k for k, v in res["artifacts"].items() if not v]
            if missing:
                print(f"  Missing Artifacts: {missing}")
            if res["error"]:
                print(f"  Error: {res["error"][:100]}...")
                
    elapsed = time.time() - start_time
    
    # Print Summary
    print("\n" + "="*60)
    print("  EVALUATION SUMMARY")
    print("="*60)
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    acceptance_rate = (passed_count / total_count) * 100 if total_count > 0 else 0
    
    print(f"Total PRDs:    {total_count}")
    print(f"Passed:        {passed_count}")
    print(f"Failed:        {total_count - passed_count}")
    print(f"Acceptance:    {acceptance_rate:.1f}%")
    print(f"Time Elapsed:  {elapsed:.1f} seconds")
    print(f"\nTarget: >70% acceptance (Phase 2 Completion Criterion)")
    
    if acceptance_rate >= 70.0:
        print("\n🎉 TARGET MET! Phase 2 Core Agents are officially validated.")
    else:
        print("\n⚠️ Target not met. Review failed PRDs and tune prompts.")
        
    print("="*60 + "\n")


if __name__ == "__main__":
    main()