import streamlit as st
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import os
from PIL import Image
import numpy as np

# Configure page
st.set_page_config(
    page_title="FCVRP Algorithm Results",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 8 rem;
        font-weight: bold;
        text-align: center;
        color: black;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .success-metric {
        border-left-color: #28a745;
    }
    .warning-metric {
        border-left-color: #ffc107;
    }
    .danger-metric {
        border-left-color: #dc3545;
    }
    .instance-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #333;
        margin: 1rem 0;
    }
    .comparison-better {
        color: #28a745;
        font-weight: bold;
    }
    .comparison-worse {
        color: #dc3545;
        font-weight: bold;
    }
    .comparison-equal {
        color: #6c757d;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    """Load all the necessary data files"""
    try:
        # Load JSON files
        with open('fcvrp_results_ILS.json', 'r') as f:
            results = json.load(f)

        with open('fcvrp_best_known.json', 'r') as f:
            best_known = json.load(f)

        # Try to load validation data if it exists
        validation_data = {}
        try:
            with open('validation_results_ILS.json', 'r') as f:
                validation_list = json.load(f)
                # Convert list to dict for easier lookup
                validation_data = {
                    os.path.basename(item['instance']): item
                    for item in validation_list
                }
        except FileNotFoundError:
            st.warning("Validation file not found. All solutions will be considered valid.")

        return results, best_known, validation_data
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return {}, {}, {}


def categorize_instances(results, validation_data):
    """Categorize instances into valid and invalid"""
    valid_instances = {}
    invalid_instances = {}

    for instance, data in results.items():
        if instance in validation_data:
            if validation_data[instance]['valid']:
                valid_instances[instance] = data
            else:
                invalid_instances[instance] = data
        else:
            # If no validation data, assume valid
            valid_instances[instance] = data

    return valid_instances, invalid_instances


def calculate_statistics(valid_instances, best_known):
    """Calculate performance statistics"""
    stats = {
        'total_instances': len(valid_instances),
        'better': 0,
        'equal': 0,
        'worse': 0,
        'total_improvement': 0,
        'total_degradation': 0,
        'compared_instances': 0
    }

    detailed_results = []

    for instance, data in valid_instances.items():
        if instance in best_known:
            stats['compared_instances'] += 1
            my_cost = data['cost']
            best_cost = best_known[instance]

            if my_cost < best_cost:
                stats['better'] += 1
                improvement = best_cost - my_cost
                stats['total_improvement'] += improvement
                status = 'Better'
                difference = improvement
            elif my_cost == best_cost:
                stats['equal'] += 1
                status = 'Equal'
                difference = 0
            else:
                stats['worse'] += 1
                degradation = my_cost - best_cost
                stats['total_degradation'] += degradation
                status = 'Worse'
                difference = degradation

            detailed_results.append({
                'Instance': instance,
                'My Cost': my_cost,
                'Best Known': best_cost,
                'Status': status,
                'Difference': difference,
                'Time (min)': round(data['solving_time_seconds'] / 60, 2)
            })

    return stats, detailed_results


def display_home_page(results, best_known, validation_data):
    """Display the home page with overall statistics"""
    st.markdown('<p class="main-header">🚛 FCVRP Algorithm Performance Dashboard</p>',
                unsafe_allow_html=True)

    # Categorize instances
    valid_instances, invalid_instances = categorize_instances(results, validation_data)

    # Calculate statistics
    stats, detailed_results = calculate_statistics(valid_instances, best_known)

    # Overall metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Instances",
            value=len(results),
            help="Total number of FCVRP instances processed"
        )

    with col2:
        valid_pct = len(valid_instances) / len(results) * 100 if results else 0
        st.metric(
            label="Valid Solutions",
            value=f"{len(valid_instances)} ({valid_pct:.1f}%)",
            help="Solutions that satisfy all FCVRP constraints"
        )

    with col3:
        invalid_pct = len(invalid_instances) / len(results) * 100 if results else 0
        st.metric(
            label="Invalid Solutions",
            value=f"{len(invalid_instances)} ({invalid_pct:.1f}%)",
            help="Solutions that violate FCVRP constraints"
        )

    with col4:
        avg_time = np.mean([data['solving_time_seconds'] for data in results.values()]) / 60
        st.metric(
            label="Average Solve Time",
            value=f"{avg_time:.2f} min",
            help="Average time to solve each instance"
        )

    st.divider()

    # Performance comparison (only for valid instances)
    if stats['compared_instances'] > 0:
        st.subheader("📊 Performance vs Best Known Solutions")

        col1, col2, col3 = st.columns(3)

        with col1:
            better_pct = stats['better'] / stats['compared_instances'] * 100
            st.metric(
                label="Better Solutions",
                value=f"{stats['better']} ({better_pct:.1f}%)",
                delta=f"Avg improvement: {stats['total_improvement'] / stats['better']:.1f}" if stats[
                                                                                                    'better'] > 0 else None,
                delta_color="normal"
            )

        with col2:
            equal_pct = stats['equal'] / stats['compared_instances'] * 100
            st.metric(
                label="Equal Solutions",
                value=f"{stats['equal']} ({equal_pct:.1f}%)",
                help="Solutions matching the best known cost"
            )

        with col3:
            worse_pct = stats['worse'] / stats['compared_instances'] * 100
            st.metric(
                label="Worse Solutions",
                value=f"{stats['worse']} ({worse_pct:.1f}%)",
                delta=f"Avg degradation: {stats['total_degradation'] / stats['worse']:.1f}" if stats[
                                                                                                   'worse'] > 0 else None,
                delta_color="inverse"
            )

        # Performance distribution chart
        performance_data = pd.DataFrame({
            'Status': ['Better', 'Equal', 'Worse'],
            'Count': [stats['better'], stats['equal'], stats['worse']],
            'Color': ['#28a745', '#6c757d', '#dc3545']
        })

        fig = px.pie(
            performance_data,
            values='Count',
            names='Status',
            title="Solution Quality Distribution",
            color_discrete_map={'Better': '#28a745', 'Equal': '#6c757d', 'Worse': '#dc3545'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

        # Detailed results table
        st.subheader("📋 Detailed Results")

        # Add filters
        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.selectbox(
                "Filter by Status:",
                ["All", "Better", "Equal", "Worse"]
            )

        with col2:
            sort_by = st.selectbox(
                "Sort by:",
                ["Instance", "My Cost", "Best Known", "Difference", "Time (min)"]
            )

        # Apply filters
        df = pd.DataFrame(detailed_results)
        if status_filter != "All":
            df = df[df['Status'] == status_filter]

        df = df.sort_values(sort_by, ascending=True if sort_by != "Difference" else False)

        # Style the dataframe
        def style_status(val):
            if val == 'Better':
                return 'color: #28a745; font-weight: bold'
            elif val == 'Worse':
                return 'color: #dc3545; font-weight: bold'
            else:
                return 'color: #6c757d; font-weight: bold'

        styled_df = df.style.map(style_status, subset=['Status'])
        st.dataframe(styled_df, use_container_width=True, height=400)

    else:
        st.warning("No comparable instances found with best known solutions.")


def display_instance_detail(instance_name, results, best_known, validation_data):
    """Display detailed view for a specific instance"""
    st.markdown(f'<p class="instance-header">📋 Instance: {instance_name}</p>',
                unsafe_allow_html=True)

    if instance_name not in results:
        st.error("Instance not found in results!")
        return

    data = results[instance_name]

    # Check if solution is valid
    is_valid = True
    if instance_name in validation_data:
        is_valid = validation_data[instance_name]['valid']

    if not is_valid:
        st.error("❌ **Invalid Solution**: Our algorithm couldn't find a feasible solution for this instance.")
        st.info("This means the solution violates one or more FCVRP constraints.")
        return

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="My Solution Cost",
            value=data['cost']
        )

    with col2:
        solving_time_min = data['solving_time_seconds'] / 60
        st.metric(
            label="Solving Time",
            value=f"{solving_time_min:.2f} min"
        )

    with col3:
        if instance_name in best_known:
            best_cost = best_known[instance_name]
            st.metric(
                label="Best Known Cost",
                value=best_cost
            )
        else:
            st.metric(
                label="Best Known Cost",
                value="N/A"
            )

    with col4:
        if instance_name in best_known:
            best_cost = best_known[instance_name]
            my_cost = data['cost']

            if my_cost < best_cost:
                st.metric(
                    label="Performance",
                    value="Better! 🎉",
                    delta=f"Improved by {best_cost - my_cost}",
                    delta_color="normal"
                )
            elif my_cost == best_cost:
                st.metric(
                    label="Performance",
                    value="Equal ✨",
                    delta="Matches best known",
                    delta_color="off"
                )
            else:
                st.metric(
                    label="Performance",
                    value="Worse 📈",
                    delta=f"Higher by {my_cost - best_cost}",
                    delta_color="inverse"
                )
        else:
            st.metric(
                label="Performance",
                value="N/A"
            )

    st.divider()

    # Display visualization and solution
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🗺️ Solution Visualization")
        viz_path = Path("Visualizations") / data['visualization_file']

        if viz_path.exists():
            try:
                image = Image.open(viz_path)
                st.image(image, caption=f"Route visualization for {instance_name}", use_container_width=True)
            except Exception as e:
                st.error(f"Error loading visualization: {e}")
        else:
            st.error("Visualization file not found!")

    with col2:
        st.subheader("📄 Solution Details")
        solution_path = Path("Solutions_ILS") / data['solution_file']

        if solution_path.exists():
            try:
                with open(solution_path, 'r') as f:
                    solution_content = f.read()

                st.text_area(
                    "Solution file content:",
                    solution_content,
                    height=400,
                    help="The actual solution routes and assignments"
                )
            except Exception as e:
                st.error(f"Error loading solution file: {e}")
        else:
            st.error("Solution file not found!")

    # Additional information
    st.subheader("ℹ️ Additional Information")
    info_col1, info_col2 = st.columns(2)

    with info_col1:
        st.write(f"**Timestamp:** {data['timestamp']}")
        st.write(f"**Solution File:** {data['solution_file']}")
        st.write(f"**Visualization File:** {data['visualization_file']}")

    with info_col2:
        # Extract instance characteristics from filename
        parts = instance_name.replace('fcvrp_', '').replace('.txt', '').split('_')
        if len(parts) >= 3:
            st.write(f"**Instance Type:** {parts[0]}")
            if len(parts) > 3:
                st.write(f"**Parameters:** {', '.join(parts[1:])}")


def main():
    """Main application"""
    # Load data
    results, best_known, validation_data = load_data()

    if not results:
        st.error("No data loaded. Please ensure all JSON files are present.")
        return

    # Sidebar navigation
    st.sidebar.title("🚛 FCVRP Results")

    # Page selection
    page = st.sidebar.selectbox(
        "Select Page:",
        ["🏠 Home", "🔍 Instance Details"]
    )

    if page == "🏠 Home":
        display_home_page(results, best_known, validation_data)

    elif page == "🔍 Instance Details":
        # Instance selection
        valid_instances, invalid_instances = categorize_instances(results, validation_data)

        st.sidebar.subheader("Select Instance")

        # Filter options
        show_valid = st.sidebar.checkbox("Show Valid Solutions", value=True)
        show_invalid = st.sidebar.checkbox("Show Invalid Solutions", value=True)

        available_instances = []
        if show_valid:
            available_instances.extend(list(valid_instances.keys()))
        if show_invalid:
            available_instances.extend(list(invalid_instances.keys()))

        available_instances.sort()

        if available_instances:
            selected_instance = st.sidebar.selectbox(
                "Choose an instance:",
                available_instances,
                help="Select an instance to view detailed results"
            )

            display_instance_detail(selected_instance, results, best_known, validation_data)
        else:
            st.warning("No instances match the current filter criteria.")

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Algorithm:** ILS (Iterated Local Search)")
    st.sidebar.markdown(f"**Total Instances:** {len(results)}")

    if validation_data:
        valid_count = sum(1 for v in validation_data.values() if v['valid'])
        invalid_count = len(validation_data) - valid_count
        st.sidebar.markdown(f"**Valid:** {valid_count} | **Invalid:** {invalid_count}")


if __name__ == "__main__":
    main()