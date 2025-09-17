import asyncio
import random
from collections import defaultdict
from time import perf_counter
from typing import Any, Dict

import httpx

# Configuration - Number of searches to run (randomly selected from available searches)
NUM_SEARCHES_TO_RUN = 30  # Change this to test different loads (max 30)

from wernicke.config.env_config.constants import EnvVar
from wernicke.engines.llm.llm_orchestrators.store.rubix.get_cell_orchestrator import (
    GetCellOrchestrator,
)
from wernicke.engines.processing.onestream_metadata.manager import RubixDimensionManager
from wernicke.engines.retrieval.helpers import get_or_create_index_config
from wernicke.engines.retrieval.index_management.factory import IndexManagerFactory
from wernicke.engines.retrieval.index_management.models import IndexService
from wernicke.engines.retrieval.retriever.initiative_retrievers.rubix_retriever import (
    RubixRetriever,
)
from wernicke.managers.cosmos_database.azure_cosmos_manager import CosmosDatabaseManager
from wernicke.tests.shared_utils.test_session import create_test_user_session


async def exec():
    print("🚀 Starting AI Search Performance Test...")
    overall_start_time = perf_counter()

    user_session_info = create_test_user_session()
    http_async_client = httpx.AsyncClient()

    # Use async context manager for Cosmos DB to avoid asyncio.run() conflict
    cosmos_db_manager = CosmosDatabaseManager(user_session_info=user_session_info)
    user_session_info.database_connection = cosmos_db_manager

    # Performance metrics storage
    performance_metrics = {"dimensions_query": 0.0, "ai_search_query": 0.0, "cosmos_queries": 0.0, "total_time": 0.0}

    try:
        rubix_manager = RubixDimensionManager(
            user_session_info=user_session_info,
            database_connection=user_session_info.database_connection,
        )

        # Get environment variables with proper type checking
        search_index_name = user_session_info.environment_config_adapter.getenv(EnvVar.RUBIX_SEARCH_INDEX_NAME)
        index_config_file = user_session_info.environment_config_adapter.getenv(EnvVar.RUBIX_INDEX_CONFIG)

        # Ensure we have string values
        if not isinstance(search_index_name, str):
            raise ValueError(f"RUBIX_SEARCH_INDEX_NAME must be a string, got {type(search_index_name)}")
        if not isinstance(index_config_file, str):
            raise ValueError(f"RUBIX_INDEX_CONFIG must be a string, got {type(index_config_file)}")

        print(f"Using search index: {search_index_name}")
        print(f"Using index config file: {index_config_file}")

        index_config = get_or_create_index_config(
            user_session_info=user_session_info,
            index_name=search_index_name,
            initiative_name=GetCellOrchestrator.__name__,
            index_config_file_name=index_config_file,
        )

        # Get all available dimensions first
        print("⏱️  Getting dimensions...")
        start_time = perf_counter()
        dimensions = await rubix_manager.get_dimensions_async()
        dimensions_time = perf_counter() - start_time
        performance_metrics["dimensions_query"] = dimensions_time
        print(f"Found {len(dimensions)} available dimensions (took {dimensions_time:.3f}s)")

        # Get the unique OS dimension types
        os_dim_types = list(set([dimension.related_dim_type for dimension in dimensions]))
        print(f"Unique dimension types: {os_dim_types}")

        # Get the dimension names for each dimension
        dimension_names = [dim.name for dim in dimensions]
        print(f"Dimension names: {dimension_names[:10]}...")  # Show first 10

        # Create index manager and use it as an async context manager
        index_manager = IndexManagerFactory.get_index_manager(
            index_service=IndexService.AZURE_COGNITIVE_SEARCH,
            user_session_info=user_session_info,
            index_name=search_index_name,
            read_timeout=30,
            connection_timeout=10,
        )

        print(f"Index manager created: {type(index_manager).__name__}")

        # Use the index manager as an async context manager to initialize the search clients
        async with index_manager:
            print("Index manager async context entered - search clients initialized")

            # Now create the retriever with properly initialized search clients
            rubix_retriever = RubixRetriever(
                user_session_info=user_session_info,
                index_service_retriever=await index_manager.as_retriever_async(
                    index_config=index_config, embedding_http_async_client=http_async_client
                ),
            )

            # Simulate the dimension reference identifier pattern
            # Example user query: "What was Northeast region revenue for Q1 2024?"
            unknown_object = "Northeast region revenue Q1 2024"
            user_query = "What was Northeast region revenue for Q1 2024?"
            print(f"🔍 User Query: '{user_query}'")
            print(f"🎯 Unknown Object: '{unknown_object}'")

            # Define all available dimension searches (30 total)
            all_dimension_searches = [
                # Revenue & Income Accounts
                {
                    "focus": "revenue accounts",
                    "search_text": "revenue sales income",
                    "target_dim_types": ["Account"],
                    "description": "Finding revenue and sales accounts",
                },
                {
                    "focus": "gross profit",
                    "search_text": "gross profit margin",
                    "target_dim_types": ["Account"],
                    "description": "Finding gross profit accounts",
                },
                {
                    "focus": "operating income",
                    "search_text": "operating income EBITDA",
                    "target_dim_types": ["Account"],
                    "description": "Finding operating income accounts",
                },
                {
                    "focus": "net income",
                    "search_text": "net income earnings",
                    "target_dim_types": ["Account"],
                    "description": "Finding net income accounts",
                },
                # Expense & Cost Accounts
                {
                    "focus": "operating expenses",
                    "search_text": "operating expenses OPEX",
                    "target_dim_types": ["Account"],
                    "description": "Finding operating expense accounts",
                },
                {
                    "focus": "cost of goods sold",
                    "search_text": "COGS cost of goods sold",
                    "target_dim_types": ["Account"],
                    "description": "Finding COGS accounts",
                },
                {
                    "focus": "SG&A expenses",
                    "search_text": "SGA selling general administrative",
                    "target_dim_types": ["Account"],
                    "description": "Finding SG&A expense accounts",
                },
                {
                    "focus": "R&D expenses",
                    "search_text": "research development RND",
                    "target_dim_types": ["Account"],
                    "description": "Finding R&D expense accounts",
                },
                # Balance Sheet Accounts
                {
                    "focus": "current assets",
                    "search_text": "current assets cash inventory",
                    "target_dim_types": ["Account"],
                    "description": "Finding current asset accounts",
                },
                {
                    "focus": "fixed assets",
                    "search_text": "fixed assets PPE property plant equipment",
                    "target_dim_types": ["Account"],
                    "description": "Finding fixed asset accounts",
                },
                {
                    "focus": "accounts receivable",
                    "search_text": "accounts receivable AR",
                    "target_dim_types": ["Account"],
                    "description": "Finding receivables accounts",
                },
                {
                    "focus": "accounts payable",
                    "search_text": "accounts payable AP",
                    "target_dim_types": ["Account"],
                    "description": "Finding payables accounts",
                },
                {
                    "focus": "long-term debt",
                    "search_text": "long term debt liabilities",
                    "target_dim_types": ["Account"],
                    "description": "Finding long-term debt accounts",
                },
                {
                    "focus": "shareholders equity",
                    "search_text": "shareholders equity retained earnings",
                    "target_dim_types": ["Account"],
                    "description": "Finding equity accounts",
                },
                # Business Units & Entities
                {
                    "focus": "cost centers",
                    "search_text": "cost centers departments",
                    "target_dim_types": ["Entity"],
                    "description": "Finding cost center entities",
                },
                {
                    "focus": "profit centers",
                    "search_text": "profit centers business units",
                    "target_dim_types": ["Entity"],
                    "description": "Finding profit center entities",
                },
                {
                    "focus": "business divisions",
                    "search_text": "business divisions segments",
                    "target_dim_types": ["Entity"],
                    "description": "Finding business division entities",
                },
                {
                    "focus": "subsidiaries",
                    "search_text": "subsidiaries affiliates",
                    "target_dim_types": ["Entity"],
                    "description": "Finding subsidiary entities",
                },
                {
                    "focus": "geographic regions",
                    "search_text": "geographic regions territories",
                    "target_dim_types": ["Entity"],
                    "description": "Finding geographic entities",
                },
                {
                    "focus": "product lines",
                    "search_text": "product lines business lines",
                    "target_dim_types": ["Entity"],
                    "description": "Finding product line entities",
                },
                {
                    "focus": "sales channels",
                    "search_text": "sales channels distribution",
                    "target_dim_types": ["Entity"],
                    "description": "Finding sales channel entities",
                },
                {
                    "focus": "manufacturing plants",
                    "search_text": "manufacturing plants facilities",
                    "target_dim_types": ["Entity"],
                    "description": "Finding manufacturing entities",
                },
                # Scenarios & Planning
                {
                    "focus": "actual results",
                    "search_text": "actual results",
                    "target_dim_types": ["Scenario"],
                    "description": "Finding actual scenario types",
                },
                {
                    "focus": "budget plan",
                    "search_text": "budget plan annual",
                    "target_dim_types": ["Scenario"],
                    "description": "Finding budget scenarios",
                },
                {
                    "focus": "forecast projection",
                    "search_text": "forecast projection rolling",
                    "target_dim_types": ["Scenario"],
                    "description": "Finding forecast scenarios",
                },
                {
                    "focus": "prior year",
                    "search_text": "prior year PY",
                    "target_dim_types": ["Scenario"],
                    "description": "Finding prior year scenarios",
                },
                # Cash Flow & Working Capital
                {
                    "focus": "cash flow operations",
                    "search_text": "cash flow operations CFO",
                    "target_dim_types": ["Account"],
                    "description": "Finding operating cash flow accounts",
                },
                {
                    "focus": "working capital",
                    "search_text": "working capital WC",
                    "target_dim_types": ["Account"],
                    "description": "Finding working capital accounts",
                },
                {
                    "focus": "capital expenditures",
                    "search_text": "capital expenditures CAPEX",
                    "target_dim_types": ["Account"],
                    "description": "Finding CAPEX accounts",
                },
                {
                    "focus": "depreciation amortization",
                    "search_text": "depreciation amortization DA",
                    "target_dim_types": ["Account"],
                    "description": "Finding depreciation accounts",
                },
            ]

            # Randomly select the specified number of searches
            if NUM_SEARCHES_TO_RUN > len(all_dimension_searches):
                print(f"⚠️  Warning: NUM_SEARCHES_TO_RUN ({NUM_SEARCHES_TO_RUN}) exceeds available searches ({len(all_dimension_searches)})")
                print(f"   Using all {len(all_dimension_searches)} available searches")
                dimension_searches = all_dimension_searches
            else:
                dimension_searches = random.sample(all_dimension_searches, NUM_SEARCHES_TO_RUN)
                print(f"🎲 Randomly selected {NUM_SEARCHES_TO_RUN} searches from {len(all_dimension_searches)} available options")

                # Show which searches were selected
                selected_focuses = [search["focus"] for search in dimension_searches]
                print(f"🎯 Selected searches: {', '.join(selected_focuses[:5])}{'...' if len(selected_focuses) > 5 else ''}")

            print(f"\n🚀 Breaking query into {len(dimension_searches)} parallel dimension searches...")

            # Create parallel search tasks for different aspects of the query
            async def search_dimension_focus(search_info: Dict[str, Any]):
                focus_start_time = perf_counter()
                print(f"  🔍 [{search_info['focus']}] Searching: '{search_info['search_text']}'")

                try:
                    # Filter dimension types to focus on relevant ones for this search aspect
                    target_types = []
                    for dim_type in os_dim_types:
                        if any(target in str(dim_type).lower() for target in [t.lower() for t in search_info["target_dim_types"]]):
                            target_types.append(dim_type)

                    # If no specific matches, use all types (fallback)
                    if not target_types:
                        target_types = os_dim_types[:2]  # Use first 2 to limit results

                    results = await rubix_retriever.retrieve_dimensions_members_async(
                        search_text=search_info["search_text"],
                        top_k=200,  # Smaller per-search to simulate real pattern
                        dim_types=target_types,
                        dim_names=dimension_names,
                        use_access_groups=True,
                    )

                    focus_time = perf_counter() - focus_start_time
                    print(f"  ✅ [{search_info['focus']}] Found {len(results)} results (took {focus_time:.3f}s)")

                    return {
                        "focus": search_info["focus"],
                        "search_text": search_info["search_text"],
                        "results": results,
                        "execution_time": focus_time,
                        "target_types": target_types,
                        "success": True,
                    }

                except Exception as e:
                    focus_time = perf_counter() - focus_start_time
                    error_type = type(e).__name__
                    print(f"  ❌ [{search_info['focus']}] {error_type}: {str(e)} (took {focus_time:.3f}s)")

                    return {
                        "focus": search_info["focus"],
                        "search_text": search_info["search_text"],
                        "results": [],
                        "execution_time": focus_time,
                        "target_types": [],
                        "success": False,
                        "error": str(e),
                        "error_type": error_type,
                    }

            # Execute all dimension-focused searches in parallel
            print("⏱️  Executing parallel dimension searches...")
            parallel_start_time = perf_counter()

            dimension_results = await asyncio.gather(*[search_dimension_focus(search_info) for search_info in dimension_searches])

            parallel_time = perf_counter() - parallel_start_time
            performance_metrics["ai_search_query"] = parallel_time

            print(f"\n🏁 All parallel dimension searches completed in {parallel_time:.3f}s")

            # Combine and analyze results
            all_retrieved_members = []
            dimension_type_results = {}

            print("\n📊 DIMENSION SEARCH RESULTS:")
            print("=" * 60)

            for result in dimension_results:
                if result["success"]:
                    all_retrieved_members.extend(result["results"])

                    print(f"🎯 {result['focus'].upper()}:")
                    print(f"   Search: '{result['search_text']}'")
                    print(f"   Target Types: {[str(t) for t in result['target_types']]}")
                    print(f"   Results: {len(result['results'])}")
                    print(f"   Time: {result['execution_time']:.3f}s")

                    # Group by dimension type
                    for member in result["results"]:
                        dim_type = str(member.dim_type)
                        if dim_type not in dimension_type_results:
                            dimension_type_results[dim_type] = []
                        dimension_type_results[dim_type].append(member)

                    # Show top results for this dimension focus
                    if result["results"]:
                        print(f"   Top matches:")
                        for i, member in enumerate(result["results"][:3]):
                            score = getattr(member, "search_score", 0)
                            name = getattr(member, "dim_member_name", "N/A")
                            print(f"     {i+1}. {name} (score: {score:.3f})")
                    print()
                else:
                    error_type = result.get("error_type", "Unknown")
                    print(f"❌ {result['focus']}: FAILED")
                    print(f"   Error Type: {error_type}")
                    print(f"   Error: {result.get('error', 'Unknown error')}")
                    print(f"   Execution Time: {result.get('execution_time', 0):.3f}s")
                    print()

            print("=" * 60)
            print(f"📈 COMBINED RESULTS BY DIMENSION TYPE:")
            for dim_type, members in dimension_type_results.items():
                print(f"   {dim_type}: {len(members)} members")

            # STRESS TEST FAILURE ANALYSIS
            print(f"\n🚨 STRESS TEST FAILURE ANALYSIS:")
            print("=" * 60)
            failed_results = [r for r in dimension_results if isinstance(r, dict) and not r.get("success", False)]
            successful_results = [r for r in dimension_results if isinstance(r, dict) and r.get("success", False)]

            print(f"📊 Success Rate: {len(successful_results)}/{len(dimension_results)} ({len(successful_results)/len(dimension_results)*100:.1f}%)")

            if failed_results:
                print(f"\n❌ FAILED SEARCHES ({len(failed_results)}):")

                # Group failures by error type
                error_types = {}
                for failure in failed_results:
                    error_type = failure.get("error_type", "Unknown")
                    if error_type not in error_types:
                        error_types[error_type] = []
                    error_types[error_type].append(failure)

                for error_type, failures in error_types.items():
                    print(f"\n  🔥 {error_type} ({len(failures)} occurrences):")
                    for failure in failures:
                        print(f"     • {failure['focus']}: {failure.get('error', 'Unknown error')[:100]}...")

                # Timing analysis for failures
                if failed_results:
                    avg_failure_time = sum(f.get("execution_time", 0) for f in failed_results) / len(failed_results)
                    print(f"\n  ⏱️  Average failure time: {avg_failure_time:.3f}s")

                    fastest_failure = min(failed_results, key=lambda x: x.get("execution_time", 0))
                    slowest_failure = max(failed_results, key=lambda x: x.get("execution_time", 0))
                    print(f"  ⚡ Fastest failure: {fastest_failure['focus']} ({fastest_failure.get('execution_time', 0):.3f}s)")
                    print(f"  🐌 Slowest failure: {slowest_failure['focus']} ({slowest_failure.get('execution_time', 0):.3f}s)")

            else:
                print(f"✅ ALL {len(dimension_results)} SEARCHES SUCCEEDED!")
                print(f"🎯 Service handled {len(dimension_results)} concurrent searches without failures")

            # Performance comparison: successes vs failures
            if successful_results and failed_results:
                avg_success_time = sum(s.get("execution_time", 0) for s in successful_results) / len(successful_results)
                avg_failure_time = sum(f.get("execution_time", 0) for f in failed_results) / len(failed_results)
                print(f"\n⚖️  PERFORMANCE COMPARISON:")
                print(f"   Successful searches avg time: {avg_success_time:.3f}s")
                print(f"   Failed searches avg time: {avg_failure_time:.3f}s")
                print(f"   Difference: {abs(avg_success_time - avg_failure_time):.3f}s")

            # SUMMARY METRICS COLLECTION
            print(f"\n📈 SUMMARY METRICS:")
            print("=" * 60)

            # Query execution time metrics
            all_times = [r.get("execution_time", 0) for r in dimension_results if isinstance(r, dict)]

            if all_times:
                print(f"⏱️  QUERY EXECUTION TIME METRICS:")
                print(f"   Total queries: {len(all_times)}")
                print(f"   Min time: {min(all_times):.3f}s")
                print(f"   Max time: {max(all_times):.3f}s")
                print(f"   Avg time: {sum(all_times)/len(all_times):.3f}s")
                print(f"   Median time: {sorted(all_times)[len(all_times)//2]:.3f}s")
                print(f"   Time range: {max(all_times) - min(all_times):.3f}s")

                # Time distribution analysis
                fast_queries = [t for t in all_times if t < 1.0]
                medium_queries = [t for t in all_times if 1.0 <= t < 3.0]
                slow_queries = [t for t in all_times if t >= 3.0]

                print(f"   Fast queries (<1s): {len(fast_queries)} ({len(fast_queries)/len(all_times)*100:.1f}%)")
                print(f"   Medium queries (1-3s): {len(medium_queries)} ({len(medium_queries)/len(all_times)*100:.1f}%)")
                print(f"   Slow queries (>3s): {len(slow_queries)} ({len(slow_queries)/len(all_times)*100:.1f}%)")

            # Results count metrics
            all_result_counts = [len(r.get("results", [])) for r in successful_results]

            if all_result_counts:
                print(f"\n📊 RESULTS COUNT METRICS:")
                print(f"   Total successful queries: {len(all_result_counts)}")
                print(f"   Min results: {min(all_result_counts)}")
                print(f"   Max results: {max(all_result_counts)}")
                print(f"   Avg results: {sum(all_result_counts)/len(all_result_counts):.1f}")
                print(f"   Median results: {sorted(all_result_counts)[len(all_result_counts)//2]}")
                print(f"   Total results across all queries: {sum(all_result_counts)}")
                print(f"   Results range: {max(all_result_counts) - min(all_result_counts)}")

                # Results distribution analysis
                no_results = [c for c in all_result_counts if c == 0]
                few_results = [c for c in all_result_counts if 1 <= c <= 10]
                medium_results = [c for c in all_result_counts if 11 <= c <= 50]
                many_results = [c for c in all_result_counts if c > 50]

                print(f"   No results (0): {len(no_results)} queries ({len(no_results)/len(all_result_counts)*100:.1f}%)")
                print(f"   Few results (1-10): {len(few_results)} queries ({len(few_results)/len(all_result_counts)*100:.1f}%)")
                print(f"   Medium results (11-50): {len(medium_results)} queries ({len(medium_results)/len(all_result_counts)*100:.1f}%)")
                print(f"   Many results (>50): {len(many_results)} queries ({len(many_results)/len(all_result_counts)*100:.1f}%)")

            # Search score analysis (from successful results)
            all_scores = []
            for result in successful_results:
                for member in result.get("results", []):
                    score = getattr(member, "search_score", 0)
                    if score > 0:
                        all_scores.append(score)

            if all_scores:
                print(f"\n🎯 SEARCH SCORE METRICS:")
                print(f"   Total scored results: {len(all_scores)}")
                print(f"   Min score: {min(all_scores):.3f}")
                print(f"   Max score: {max(all_scores):.3f}")
                print(f"   Avg score: {sum(all_scores)/len(all_scores):.3f}")
                print(f"   Median score: {sorted(all_scores)[len(all_scores)//2]:.3f}")
                print(f"   Score range: {max(all_scores) - min(all_scores):.3f}")

                # Score distribution analysis
                low_scores = [s for s in all_scores if s < 0.5]
                medium_scores = [s for s in all_scores if 0.5 <= s < 0.8]
                high_scores = [s for s in all_scores if s >= 0.8]

                print(f"   Low relevance (<0.5): {len(low_scores)} results ({len(low_scores)/len(all_scores)*100:.1f}%)")
                print(f"   Medium relevance (0.5-0.8): {len(medium_scores)} results ({len(medium_scores)/len(all_scores)*100:.1f}%)")
                print(f"   High relevance (>=0.8): {len(high_scores)} results ({len(high_scores)/len(all_scores)*100:.1f}%)")

            # Efficiency metrics
            if successful_results:
                print(f"\n⚡ EFFICIENCY METRICS:")
                efficiency_scores = []
                for result in successful_results:
                    time = result.get("execution_time", 1)  # Avoid division by zero
                    count = len(result.get("results", []))
                    if time > 0:
                        efficiency = count / time  # results per second
                        efficiency_scores.append(efficiency)

                if efficiency_scores:
                    print(f"   Min efficiency: {min(efficiency_scores):.1f} results/sec")
                    print(f"   Max efficiency: {max(efficiency_scores):.1f} results/sec")
                    print(f"   Avg efficiency: {sum(efficiency_scores)/len(efficiency_scores):.1f} results/sec")
                    print(f"   Median efficiency: {sorted(efficiency_scores)[len(efficiency_scores)//2]:.1f} results/sec")
                    print(f"   Efficiency range: {max(efficiency_scores) - min(efficiency_scores):.1f} results/sec")

            # Overall system performance summary
            print(f"\n🏆 SYSTEM PERFORMANCE SUMMARY:")
            total_time = parallel_time
            total_results = sum(all_result_counts) if all_result_counts else 0
            success_rate = len(successful_results) / len(dimension_results) * 100 if dimension_results else 0

            print(f"   Overall success rate: {success_rate:.1f}%")
            print(f"   Total execution time: {total_time:.3f}s")
            print(f"   Total results retrieved: {total_results}")
            print(f"   Overall throughput: {total_results/total_time:.1f} results/sec" if total_time > 0 else "   Overall throughput: N/A")
            print(f"   Concurrent load: {len(dimension_results)} parallel searches")
            print(f"   Average query latency: {sum(all_times)/len(all_times):.3f}s" if all_times else "   Average query latency: N/A")

            print(f"\n⏱️  DETAILED AI SEARCH TIMING BREAKDOWN:")
            print("=" * 60)
            total_individual_time = 0
            successful_searches = 0

            for result in dimension_results:
                if result["success"]:
                    successful_searches += 1
                    total_individual_time += result["execution_time"]
                    efficiency = len(result["results"]) / result["execution_time"] if result["execution_time"] > 0 else 0
                    print(f"🔍 {result['focus']}: {result['execution_time']:.3f}s → {len(result['results'])} results ({efficiency:.1f} results/sec)")

            if successful_searches > 0:
                avg_search_time = total_individual_time / successful_searches
                time_saved = total_individual_time - parallel_time
                efficiency_gain = (time_saved / total_individual_time) * 100 if total_individual_time > 0 else 0

                print(f"\n📊 PARALLEL EXECUTION ANALYSIS:")
                print(f"   Sequential execution would take: {total_individual_time:.3f}s")
                print(f"   Parallel execution took: {parallel_time:.3f}s")
                print(f"   Time saved: {time_saved:.3f}s ({efficiency_gain:.1f}% faster)")
                print(f"   Average per search: {avg_search_time:.3f}s")

            retrieved_dimension_members = all_retrieved_members
            print(f"\n🎯 Total combined results: {len(retrieved_dimension_members)} members")
            print(f"⚡ Parallel execution advantage: Searched {len(dimension_searches)} aspects simultaneously")

            # Re-split by os_dim_type so that we can query cosmos across each dimension type (since db is partitioned by dimension type)
            os_dim_type_to_members = defaultdict(list)
            for retrieved_dim_member in retrieved_dimension_members:
                os_dim_type_to_members[retrieved_dim_member.dim_type].append(retrieved_dim_member)

            print(f"Grouped by dimension types: {list(os_dim_type_to_members.keys())}")

            # Get the dimension members from the Rubix manager
            print("⏱️  Getting detailed dimension info from Cosmos DB...")
            cosmos_start_time = perf_counter()
            all_retrieved_dim_members = []

            for dim_type, dim_members in os_dim_type_to_members.items():
                print(f"  📊 Getting detailed info for {len(dim_members)} members of type {dim_type}")
                dim_type_start_time = perf_counter()
                dim_members_detailed = await rubix_manager.get_dim_members_async(
                    dim_type=dim_type, dim_member_names=[dim_member.dim_member_name for dim_member in dim_members]
                )
                dim_type_time = perf_counter() - dim_type_start_time
                print(f"    ✅ Got {len(dim_members_detailed)} detailed members (took {dim_type_time:.3f}s)")
                all_retrieved_dim_members.extend(dim_members_detailed)

            cosmos_time = perf_counter() - cosmos_start_time
            performance_metrics["cosmos_queries"] = cosmos_time
            print(f"\n📋 Final results: {len(all_retrieved_dim_members)} detailed dimension members (Cosmos queries took {cosmos_time:.3f}s total)")

            # Print some results
            for i, member in enumerate(all_retrieved_dim_members[:5]):  # Show first 5
                print(f"  {i+1}. {getattr(member, 'name', 'N/A')} (type: {getattr(member, 'dim_type', 'N/A')})")

            # Calculate and display performance summary
            total_time = perf_counter() - overall_start_time
            performance_metrics["total_time"] = total_time

            print("\n" + "=" * 60)
            print("🔥 PERFORMANCE METRICS SUMMARY")
            print("=" * 60)
            print(
                f"⚡ Dimensions Query:     {performance_metrics['dimensions_query']:.3f}s ({performance_metrics['dimensions_query']/total_time*100:.1f}%)"
            )
            print(
                f"🔍 AI Search Query:      {performance_metrics['ai_search_query']:.3f}s ({performance_metrics['ai_search_query']/total_time*100:.1f}%)"
            )
            print(
                f"💾 Cosmos DB Queries:    {performance_metrics['cosmos_queries']:.3f}s ({performance_metrics['cosmos_queries']/total_time*100:.1f}%)"
            )
            print(f"🏁 Total Execution Time: {total_time:.3f}s")
            print("=" * 60)

            # Performance insights
            slowest_operation = max(performance_metrics.items(), key=lambda x: x[1] if x[0] != "total_time" else 0)
            print(f"🐌 Slowest operation: {slowest_operation[0].replace('_', ' ').title()} ({slowest_operation[1]:.3f}s)")

            if parallel_time > 0:
                throughput = len(retrieved_dimension_members) / parallel_time
                print(f"🚀 AI Search Throughput: {throughput:.1f} results/second")
                print(f"📊 Retrieved {len(retrieved_dimension_members)} results, got {len(all_retrieved_dim_members)} detailed records")

                # Show individual search timings
                print(f"🔍 Individual Search Timings:")
                for result in dimension_results:
                    if isinstance(result, dict) and result["success"]:
                        focus_throughput = len(result["results"]) / result["execution_time"] if result["execution_time"] > 0 else 0
                        print(f"   {result['focus']}: {result['execution_time']:.3f}s ({focus_throughput:.1f} results/sec)")

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        import traceback

        traceback.print_exc()

    finally:
        await http_async_client.aclose()
        # Clean up Cosmos DB connection manually since we're not using context manager
        try:
            if hasattr(cosmos_db_manager, "_cosmos_client_async"):
                cosmos_client = getattr(cosmos_db_manager, "_cosmos_client_async", None)
                if cosmos_client:
                    await cosmos_client.close()
        except Exception as cleanup_error:
            print(f"Warning: Failed to close Cosmos client: {cleanup_error}")


if __name__ == "__main__":
    asyncio.run(exec())
