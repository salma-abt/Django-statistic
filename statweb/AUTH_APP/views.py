from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login,logout,authenticate
from django.contrib.auth.views import LoginView
from django.http import HttpResponse
from django.contrib import messages
from .forms import CustomLoginForm
import matplotlib.dates as mdates
from django.conf import settings
from django.urls import reverse
import matplotlib.pyplot as plt
from scipy.stats import bernoulli
from scipy.stats import poisson
from scipy.stats import binom
from scipy.stats import expon
from scipy.stats import norm
from io import BytesIO
import seaborn as sns
from .models import *
import matplotlib 
matplotlib.use('Agg')
from .forms import *
import pandas as pd
import numpy as np
import itertools
import base64
import math
import io
import os


def home(request):
    return render(request, 'navbar.html',{})

def user_files(request):
    if request.user.is_authenticated:
        user_files = UserExcelFile.objects.filter(user=request.user)
        return render(request, 'user_files.html', {'user_files': user_files})
    else:
        return render(request, 'login.html')
    
def delete_file(request, file_id):
    if request.user.is_authenticated:
        file_to_delete = get_object_or_404(UserExcelFile, id=file_id, user=request.user)
        file_to_delete.file.delete()  
        file_to_delete.delete() 
        messages.success(request, 'File deleted successfully.')
        return redirect('user_files')
    else:
        return render(request, 'login.html')
    
def sign_up(request):
    if request.user.is_authenticated:
        return redirect('home')
    else:
        if request.method == "POST":
            form = UsersForm(request.POST or None)
            if form.is_valid():
                form.save()
                messages.success(request, 'Your account has been created successfully!')
                return redirect('sign_up')   
            else:           
                messages.error(request, "There was a problem creating your account!")
        else:
            form = UsersForm()
        return render(request, 'sign_up.html', {'form' : form})

class CustomLoginView(LoginView):
    form_class = CustomLoginForm

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, 'login.html', {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request=request)
        if form.is_valid():
            user = authenticate(request=request, username=form.cleaned_data['email'], password=form.cleaned_data['motdepass'])
            if user is not None:
                login(request, user)
                return redirect('home')  
        else:
            messages.error(request, "Invalid email or password!")
        return render(request, 'login.html', {'form': form})


def logoutUser(request):
    logout(request)
    return redirect(reverse('login'))




def upload_excel(request):
    if request.user.is_authenticated:
        data_frame_html = None
        if request.method == 'POST':
            form = ExcelUploadForm(request.POST, request.FILES, user=request.user)
            if form.is_valid():
                excel_file = form.cleaned_data.get('file')
                custom_name = form.cleaned_data.get('name')
                user_excel_file = UserExcelFile(
                    user=request.user,
                    file=excel_file,
                    name=custom_name
                )
                user_excel_file.save()
                data_frame = pd.read_excel(user_excel_file.file.path)
                sliced_data_frame = data_frame.head(20)
                data_frame_html = sliced_data_frame.to_html(classes='table table-bordered table-striped', index=False)

        else:
            form = ExcelUploadForm(user=request.user)

        return render(request, 'upload_excel.html', {
            'form': form,
            'data_frame_html': data_frame_html,
        })

    else:
        return redirect('login')

def view_file(request, file_id):
    user_file = get_object_or_404(UserExcelFile, id=file_id, user=request.user)

    file_path = user_file.file.path
    data_frame = pd.read_excel(file_path)

    row_limit = int(request.GET.get('row_limit', 10))

    sliced_data_frame = data_frame.head(row_limit)

    data_frame_html = sliced_data_frame.to_html(classes='table table-bordered table-striped', index=False)

    return render(request, 'view_file.html', {
        'data_frame_html': data_frame_html,
        'file_name': user_file.name,
        'row_limit': row_limit,
        'file_id': user_file.id
    })

def index_file(request, file_id):
    # Fetch the user's uploaded file
    user_file = get_object_or_404(UserExcelFile, id=file_id, user=request.user)
    data_frame = pd.read_excel(user_file.file.path)

    # Convert DataFrame to HTML to show the original data
    original_data_html = data_frame.to_html(classes='table table-bordered table-striped', index=True)
    indexed_data_html = None

    if request.method == 'POST':
        # Get column and index values from the user
        column_name = request.POST.get('column_name')  # Selected column name
        index_value = request.POST.get('index_value')  # Row index value

        try:
            # Ensure both column name and index value are provided
            if column_name and index_value:
                index_value = int(index_value)  # Convert index_value to an integer if it's numeric
                column_name = str(column_name)
                
                # Fetch the value using .loc[]
                indexed_value = data_frame.loc[index_value, column_name]
                
                # Convert the scalar value to a DataFrame for display
                indexed_data = pd.DataFrame({column_name: [indexed_value]})
                indexed_data_html = indexed_data.to_html(classes='table table-bordered table-striped', index=False)
            else:
                indexed_data_html = "<p style='color:red;'>Please provide both column name and index value.</p>"
        except (KeyError, ValueError) as e:
            indexed_data_html = f"<p style='color:red;'>Invalid column name or index value provided. Error: {str(e)}</p>"

    return render(request, 'index_file.html', {
        'file_name': user_file.name,
        'original_data_html': original_data_html,
        'file_id': user_file.id,
        'indexed_data_html': indexed_data_html,
        'columns': data_frame.columns.tolist(),
    })

def slice_file(request, file_id):
    # Fetch the user's file
    user_file = get_object_or_404(UserExcelFile, id=file_id, user=request.user)
    file_path = user_file.file.path
    data_frame = pd.read_excel(file_path)
    quantitative = data_frame.select_dtypes(include=["int64", "float64"]).columns.tolist()
    if 'ID' in quantitative:
        quantitative.remove('ID')
    if 'id' in quantitative:
        quantitative.remove('id')
    qualitative = data_frame.select_dtypes(include=["object", "category"]).columns.tolist()
    hue_columns = [
        col for col in qualitative if data_frame[col].nunique() <= 10
    ]
    discrete_columns = quantitative[:]
    contin_columns =hue_columns[:]
    for column in quantitative:
        unique_values = data_frame[column].nunique()  # Number of unique values
        total_values = len(data_frame[column])  # Total number of entries in the column
        
        if data_frame[column].dtype in ['int64', 'float64']:  # Check for numeric columns
            # If unique values are less than 20% of total, it's likely a discrete column
            if unique_values < total_values * 0.2:
                discrete_columns.remove(column)
                contin_columns.append(column)
    # Default row limit and sliced data
    sliced_data_frame = data_frame.head(10)

    # Determine whether ascending or descending form was submitted
    asc_row_limit = request.GET.get('asc_row_limit')
    desc_row_limit = request.GET.get('desc_row_limit')
    disp_row = request.GET.get('disp_row')
    start_column = request.GET.get('start_column')
    end_column = request.GET.get('end_column')
    start_row = request.GET.get('start_row')
    end_row = request.GET.get('end_row')
    srow = request.GET.get('srow')
    erow = request.GET.get('erow')
    groupby_column = request.GET.get('groupby_column', None)
    aggregation_column = request.GET.getlist('aggregation_column', None)
    aggregation_type = request.GET.get('aggregation_type', 'sum')
    multiple_columns = request.GET.getlist('multiple_columns')
    start_row = int(start_row) - 1 if start_row else None
    end_row = int(end_row) - 1 if end_row else None
    srow = int(srow) - 1 if srow else None
    erow = int(erow) - 1 if erow else None
    if asc_row_limit:
        row_limit = int(asc_row_limit)
        sliced_data_frame = data_frame.head(row_limit)
    elif desc_row_limit:
        row_limit = int(desc_row_limit)
        sliced_data_frame = data_frame.tail(row_limit)
    elif disp_row:
        try:
            # Fetch the single row by its index
            row_index = int(disp_row)-1
            single_row = data_frame.iloc[row_index]  # Fetch the specific row
            sliced_data_frame = single_row.to_frame().T  # Convert Series to DataFrame
        except (IndexError, ValueError):
            sliced_data_frame = pd.DataFrame(
                {"Error": ["Row index is out of range or invalid."]}
            )
    elif start_column or end_column or start_row or end_row :
        try:
            sliced_data_frame = data_frame.loc[start_row:end_row, start_column:end_column]
        except (KeyError, IndexError, ValueError) as e:
            sliced_data_frame = pd.DataFrame({"Error": [f"Invalid input: {str(e)}"]})
    elif srow or erow or multiple_columns:
        try:
            sliced_data_frame = data_frame.loc[srow:erow, multiple_columns]
        except (KeyError, IndexError, ValueError) as e:
            sliced_data_frame = pd.DataFrame({"Error": [f"Invalid input: {str(e)}"]})
    elif groupby_column and aggregation_column:
        try:
            grouped_frame = data_frame.groupby(groupby_column)[aggregation_column].agg(aggregation_type)
            sliced_data_frame = grouped_frame.reset_index()
        except Exception as e:
            sliced_data_frame = f"<p>Error in processing: {str(e)}</p>"
    
    data_frame_html = sliced_data_frame.to_html(classes='table table-bordered table-striped', index=False)

    return render(request, 'slice_file.html', {
        'data_frame_html': data_frame_html,
        'file_name': user_file.name,
        'file_id': user_file.id,
        'columns': data_frame.columns.tolist(),
        'multiple_columns': multiple_columns,
        'grouped_data_html': sliced_data_frame,
        'quantitative':quantitative,
        'hue_columns': hue_columns,
        'discrete_columns': discrete_columns,
        'contin_columns': contin_columns
    })


def vis_file(request, file_id):
    user_file = get_object_or_404(UserExcelFile, id=file_id, user=request.user)

    file_path = user_file.file.path
    data_frame = pd.read_excel(file_path)

    # Identify quantitative and date columns
    quantitative = data_frame.select_dtypes(include=["int64", "float64"]).columns.tolist()
    if 'ID' in quantitative:
        quantitative.remove('ID')
    if 'id' in quantitative:
        quantitative.remove('id')
    date_columns = data_frame.select_dtypes(include=["datetime64"]).columns.tolist()
    qualitative = data_frame.select_dtypes(include=["object", "category"]).columns.tolist()
    hue_columns = [
        col for col in qualitative if data_frame[col].nunique() <= 10
    ]
    discrete_columns = hue_columns[:]

    for column in quantitative:
        unique_values = data_frame[column].nunique()  # Number of unique values
        total_values = len(data_frame[column])  # Total number of entries in the column
        
        if data_frame[column].dtype in ['int64', 'float64']:  # Check for numeric columns
            # If unique values are less than 20% of total, it's likely a discrete column
            if unique_values < total_values * 0.2:
                discrete_columns.append(column)
    hue_orders = {
        col: data_frame[col].dropna().unique().tolist() for col in hue_columns
    }
    row_limit = 10
    sliced_data_frame = data_frame.head(row_limit)
    data_frame_html = sliced_data_frame.to_html(classes='table table-bordered table-striped', index=False)

    # Variables for plots
    box_plot_data = None
    line_plot_data = None
    scatter_plot_data = None
    selected_date_column = None
    hist_plot_data = None
    selected_quantitative_column = None
    selected_kde_x = None
    kde_plot_data = None
    selected_scatter_x = None
    selected_scatter_y = None
    selected_box_x = None
    selected_violin_x = None
    violin_plot_data = None
    selected_violin_hue = None
    selected_box_y = None
    selected_hue = None  # Ensure selected_hue is initialized as None
    selected_hue_b= None
    selected_violin_y= None
    selected_xhist = None
    bar_plot_data = None
    heatmap_data = None
    pie_plot_data = None
    selected_bar_x = None
    selected_bar_y = None
    selected_hhist = None
    selected_pie_x = None
    stat_options = ["count", "frequency", "probability", "density", "percent"]
    selected_stat = None
    hue_order = []

    # Handle form submission for line plot
    if request.method == "GET" and 'xcolumn' in request.GET and 'ycolumn' in request.GET:
        selected_date_column = request.GET['xcolumn']
        selected_quantitative_column = request.GET['ycolumn']

        if selected_date_column and selected_quantitative_column:
            try:
                # Generate the line plot with a smaller size
                plt.figure(figsize=(8, 4))  # Smaller plot dimensions
                sns.set(style="whitegrid")
                sns.lineplot(
                    x=data_frame[selected_date_column],
                    y=data_frame[selected_quantitative_column],
                    marker='o', color='b', label=selected_quantitative_column
                )
                plt.xlabel(selected_date_column)
                plt.ylabel(selected_quantitative_column)
                plt.title(f"Line Plot of {selected_quantitative_column} over {selected_date_column}")
        
                # Format dates on the X-axis
                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d-%m-%Y'))
                plt.xticks(rotation=15)

                # Add legend and save plot to a BytesIO buffer
                plt.legend()
                buf = BytesIO()
                plt.savefig(buf, format='png')
                buf.seek(0)
                line_plot_data = base64.b64encode(buf.getvalue()).decode('utf-8')
                buf.close()
                plt.close()
            except Exception as e:
                print(f"Error generating line plot: {e}")

    # Handle form submission for scatter plot
    if request.method == "GET" and 'xscatter' in request.GET and 'yscatter' in request.GET:
        selected_scatter_x = request.GET['xscatter']
        selected_scatter_y = request.GET['yscatter']

        # Ensure selected_hue is always defined, even if not selected
        selected_hue = request.GET.get('hue_columns', None)  # Default to None if not selected
        hue_order = request.GET.getlist('hue_order')  # List of selected hue order items
        enable_kde = request.GET.get('kdePlot', 'off') == 'on'  # Check if KDE plot is enabled

        if selected_scatter_x and selected_scatter_y:
            try:
                # Generate scatter plot
                plt.figure(figsize=(8, 4))
                sns.set(style="whitegrid")

                # Create scatter plot with or without hue and hue order
                scatter_kwargs = {
                    "x": data_frame[selected_scatter_x],
                    "y": data_frame[selected_scatter_y],
                    "color": 'g'
                }
                if selected_hue and selected_hue in data_frame.columns:
                    scatter_kwargs.update({
                        "hue": data_frame[selected_hue],
                        "palette": "viridis"  # Optional palette for better visualization
                    })
                    if hue_order:
                        scatter_kwargs["hue_order"] = hue_order

                sns.scatterplot(**scatter_kwargs)

                if enable_kde:
                    sns.kdeplot(
                        x=data_frame[selected_scatter_x],
                        y=data_frame[selected_scatter_y],
                        hue=data_frame[selected_hue] if selected_hue in data_frame.columns else None,
                        hue_order=hue_order,
                        palette="viridis" if selected_hue in data_frame.columns else None,
                        fill=True,  # Fill under the density curve
                        thresh=0,  # Lower threshold for curve plotting
                        levels=100,  # Number of contour levels
                        alpha=0.5  # Transparency of the fill
                    )

                plt.xlabel(selected_scatter_x)
                plt.ylabel(selected_scatter_y)
                plt.title(
                    f"Scatter Plot of {selected_scatter_y} and {selected_scatter_x}"
                    + (f" by {selected_hue}" if selected_hue else "")
                )

                # Save plot to BytesIO buffer
                buf = BytesIO()
                plt.savefig(buf, format='png')
                buf.seek(0)
                scatter_plot_data = base64.b64encode(buf.getvalue()).decode('utf-8')
                buf.close()
                plt.close()
            except Exception as e:
                print(f"Error generating scatter plot: {e}")

    if request.method == "GET" and 'xbox' in request.GET:
        selected_box_x = request.GET.get('xbox')  # Quantitative
        selected_box_y = request.GET.get('ybox' , None)  # Categorical
        selected_hue_b = request.GET.get('hbox', None)
        if selected_box_x:
            try:
                # Create the plot
                plt.figure(figsize=(10, 6))
            
                # Check if both y_column and hue are provided
                if selected_box_y:
                    if selected_hue_b:  # If hue is provided
                        sns.boxplot(
                            data=data_frame,
                            x=selected_box_x,
                            y=selected_box_y,
                            hue=selected_hue_b
                        )
                        title = f"Box Plot of {selected_box_x} by {selected_box_y} with hue {selected_hue_b}"
                    else:  # No hue, but y_column is provided
                        sns.boxplot(
                            data=data_frame,
                            x=selected_box_x,
                            y=selected_box_y
                        )
                        title = f"Box Plot of {selected_box_x} by {selected_box_y}"
                else:  # No y_column, but check for hue
                    if selected_hue_b:  # Only hue is provided
                        sns.boxplot(
                            data=data_frame,
                            x=selected_box_x,
                            hue=selected_hue_b
                        )
                        title = f"Box Plot of {selected_box_x} with hue {selected_hue_b}"
                    else:  # Neither y_column nor hue
                        sns.boxplot(
                            data=data_frame,
                            x=selected_box_x
                        )
                        title = f"Box Plot of {selected_box_x}"
                # Save the plot to a BytesIO object
                plt.title(title)
                plt.tight_layout()
                buffer = BytesIO()
                plt.savefig(buffer, format="png")
                buffer.seek(0)
                box_plot_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
                buffer.close()
                plt.close()
            except Exception as e:
                print(f"Error generating box plot: {e}")
    if request.method == "GET" and 'xhist' in request.GET:
        selected_xhist = request.GET.get('xhist', None)
        selected_stat = request.GET.get('yhist')
        selected_hhist = request.GET.get('hhist', None)
        if selected_xhist:
            try:
                # Create the plot
                plt.figure(figsize=(10, 6))
            
                # Check if the selected stat is valid and create the plot accordingly
                if selected_hhist:  # If hue is selected
                    sns.histplot(data=data_frame, x=selected_xhist, stat=selected_stat, hue=selected_hhist,kde=True)
                    plt.title(f"Histogram of {selected_xhist} with {selected_stat} by {selected_hhist}")
                else:  # If no hue is provided
                    sns.histplot(data=data_frame, x=selected_xhist, stat=selected_stat,kde=True)
                    plt.title(f"Histogram of {selected_xhist} with {selected_stat}")
            
                plt.tight_layout()

                # Save the plot to a BytesIO object
                buffer = BytesIO()
                plt.savefig(buffer, format="png")
                buffer.seek(0)
                hist_plot_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
                buffer.close()
                plt.close()

            except Exception as e:
                print(f"Error generating histogram: {e}")
    if request.method == "GET" and 'xkde' in request.GET:
        selected_kde_x = request.GET.get('xkde', None)

        if selected_kde_x:
            try:
                plt.figure(figsize=(10, 6))
                sns.kdeplot(data=data_frame[selected_kde_x], fill=True)
                plt.title(f"KDE Plot of {selected_kde_x}")
                plt.xlabel(selected_kde_x)
                plt.ylabel('Density')

                buffer = BytesIO()
                plt.savefig(buffer, format="png")
                buffer.seek(0)
                kde_plot_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
                buffer.close()
                plt.close()

            except Exception as e:
                print(f"Error generating KDE plot: {e}")
    if request.method == "GET" and 'xvio' in request.GET:
        selected_violin_x = request.GET.get('xvio', None)  # Quantitative
        selected_violin_hue = request.GET.get('hue_violin', None)  # Optional hue parameter
        selected_violin_y = request.GET.get('yvio', None)

        if selected_violin_x:
            try:
                # Create the plot
                plt.figure(figsize=(10, 6))
                sns.set(style="whitegrid")
            
                # Prepare violin plot arguments
                plot_args = {
                    'x': selected_violin_x,
                    'data': data_frame,
                    'inner': 'quartile',
                    'palette': 'muted'
                }

                # Conditionally add y-axis and hue to the plot arguments if provided
                if selected_violin_y:
                    plot_args['y'] = data_frame[selected_violin_y]
            
                if selected_violin_hue and selected_violin_hue in data_frame.columns:
                    plot_args['hue'] = data_frame[selected_violin_hue]
                    plot_args['split'] = True  # Split the violin by hue if hue is specified

                sns.violinplot(**plot_args)
                plt.title(f"Violin Plot of {selected_violin_x}" + 
                      (f" by {selected_violin_hue}" if selected_violin_hue else "") + 
                      (f" and {selected_violin_y}" if selected_violin_y else ""))
                plt.xlabel(selected_violin_x)

                # Save the plot to a BytesIO object
                buffer = BytesIO()
                plt.savefig(buffer, format="png")
                buffer.seek(0)
                violin_plot_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
                buffer.close()
                plt.close()
            except Exception as e:
                print(f"Error generating violin plot: {e}")
    if request.method == "GET" and 'xbar' in request.GET:
        selected_bar_x = request.GET.get('xbar', None)  # Mandatory X-axis
        selected_bar_y = request.GET.get('ybar', None)  # Optional Y-axis

        if selected_bar_x:
            try:
                # Create the plot
                plt.figure(figsize=(10, 6))
                sns.set(style="whitegrid")
            
                # Prepare bar plot arguments
                if selected_bar_y:
                    # If Y-axis is provided, use it for the bar plot
                    sns.barplot(x=selected_bar_x, y=selected_bar_y, data=data_frame, palette='viridis')
                    plt.ylabel(selected_bar_y)
                    plt.title(f"Bar Plot of {selected_bar_x} by {selected_bar_y}")
                else:
                    # If no Y-axis is provided, use the count of X-axis categories
                    sns.countplot(x=selected_bar_x, data=data_frame,hue=selected_bar_x, palette='viridis')
                    plt.ylabel('Count')
                    plt.title(f"Bar Plot of {selected_bar_x}")

                plt.xlabel(selected_bar_x)

                # Save the plot to a BytesIO object
                buffer = BytesIO()
                plt.savefig(buffer, format="png")
                buffer.seek(0)
                bar_plot_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
                buffer.close()
                plt.close()
            except Exception as e:
                print(f"Error generating bar plot: {e}")
    if request.method == "GET" and 'xpie' in request.GET:
        selected_pie_x = request.GET.get('xpie')  # The categorical column for pie chart
    
        if selected_pie_x:
            try:
                # Aggregate data to get counts for each category
                pie_data = data_frame[selected_pie_x].value_counts()
            
                # Create the plot
                plt.figure(figsize=(8, 8))
                plt.pie(pie_data, labels=pie_data.index,colors=sns.color_palette('pastel'), autopct='%1.1f%%', startangle=140)
                plt.title(f"Pie Chart of {selected_pie_x}")
                plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
            
                # Save the plot to a BytesIO object
                buffer = BytesIO()
                plt.savefig(buffer, format="png")
                buffer.seek(0)
                pie_plot_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
                buffer.close()
                plt.close()
            except Exception as e:
                print(f"Error generating pie chart: {e}")
    if request.method == "GET":
        try:
            # Select only the quantitative columns for the correlation matrix
            data_selected = data_frame[quantitative]
        
            # Compute the correlation matrix
            correlation_matrix = data_selected.corr()
        
            # Create the heatmap
            plt.figure(figsize=(12, 10))
            sns.heatmap(correlation_matrix, annot=True, fmt=".2f", cmap='coolwarm', cbar=True)
            plt.title("Heatmap of Correlation Between Quantitative Variables")
        
            # Save the plot to a BytesIO object
            buffer = BytesIO()
            plt.savefig(buffer, format="png")
            buffer.seek(0)
            heatmap_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
            buffer.close()
            plt.close()

        except Exception as e:
            print(f"Error generating heatmap: {e}")

    return render(request, 'vis_file.html', {
        'data_frame_html': data_frame_html,
        'file_name': user_file.name,
        'row_limit': row_limit,
        'file_id': user_file.id,
        'quantitative': quantitative,
        'qualitative': qualitative,
        'date_columns': date_columns,
        'line_plot_data': line_plot_data,
        'scatter_plot_data': scatter_plot_data,
        'selected_date_column': selected_date_column,
        'selected_quantitative_column': selected_quantitative_column,
        'selected_scatter_x': selected_scatter_x,
        'selected_scatter_y': selected_scatter_y,
        'hue_columns': hue_columns,
        'hue_orders': hue_orders,
        'violin_plot_data':violin_plot_data,
        'selected_hue': selected_hue,  # Pass the selected hue to the template
        'hue_order': hue_order,  # Pass the hue order to the template
        'request_GET_hue_order': request.GET.getlist('hue_order'),
        'box_plot_data': box_plot_data,
        'selected_box_x': selected_box_x,
        'selected_box_y': selected_box_y,
        'selected_hue_b': selected_hue_b,
        'stat_options': stat_options,
        'selected_xhist': selected_xhist,
        'selected_stat': selected_stat,
        'hist_plot_data': hist_plot_data,
        'selected_hhist': selected_hhist,
        'discrete_columns': discrete_columns,
        'selected_kde_x': selected_kde_x,
        'kde_plot_data': kde_plot_data,
        'selected_violin_x': selected_violin_x,
        'selected_violin_hue': selected_violin_hue,
        'selected_violin_y': selected_violin_y,
        'bar_plot_data': bar_plot_data,
        'selected_bar_y': selected_bar_y,
        'selected_bar_x': selected_bar_x,
        'heatmap_data': heatmap_data,
        'selected_pie_x': selected_pie_x,
        'pie_plot_data': pie_plot_data,
    })



def prob_file(request,file_id):
    user_file = get_object_or_404(UserExcelFile, id=file_id, user=request.user)

    file_path = user_file.file.path
    data_frame = pd.read_excel(file_path)
    quantitative = data_frame.select_dtypes(include=["int64", "float64"]).columns.tolist()
    if 'ID' in quantitative:
        quantitative.remove('ID')
    if 'id' in quantitative:
        quantitative.remove('id')
    date_columns = data_frame.select_dtypes(include=["datetime64"]).columns.tolist()
    qualitative = data_frame.select_dtypes(include=["object", "category"]).columns.tolist()
    hue_columns = [
        col for col in qualitative if data_frame[col].nunique() <= 10
    ]
    discrete_columns = hue_columns[:]
    mode = quantitative[:] + hue_columns[:]
    for column in quantitative:
        unique_values = data_frame[column].nunique()  # Number of unique values
        total_values = len(data_frame[column])  # Total number of entries in the column
        
        if data_frame[column].dtype in ['int64', 'float64']:  # Check for numeric columns
            # If unique values are less than 20% of total, it's likely a discrete column
            if unique_values < total_values * 0.2:
                discrete_columns.append(column)

    mean_column = request.GET.get('mcolumn',None)
    median_column = request.GET.get('mecolumn',None)
    mode_column = request.GET.get('ycolumn',None)
    std_column = request.GET.get('stdcolumn',None)
    var_column = request.GET.get('vcolumn',None)
    ran_column = request.GET.get('rcolumn',None)
    mu = float(request.GET.get('mu', 0))  # Default mean is 0
    sigma = float(request.GET.get('sigma', 0))
    bin_plot_data = None
    norm_plot_data = None
    poi_plot_data = None
    uni_plot_data = None
    a = float(request.GET.get('a', 0))  # Default minimum is 0
    b = float(request.GET.get('b', 0))  # Default maximum is 1
    lambda_value = float(request.GET.get('lambda', 0))
    pb = float(request.GET.get('probabilityb', -1))
    n = int(request.GET.get('trials', 0))
    p = float(request.GET.get('probability', 0))
    rate = float(request.GET.get('lambdae', 0))  # Default rate is 1
    exp_plot_data = None
    ber_plot_data = None
    var_result = None
    std_result = None
    range_result = None
    results = {}

    # Calculate mean if a column is selected for it
    if ran_column:
        try:
            max_value = data_frame[ran_column].max()
            min_value = data_frame[ran_column].min()
            range_result = max_value - min_value  # Calculate the range
        except Exception as e:
            range_result = f"Error calculating range: {str(e)}"
    if mean_column:
        try:
            results['mean'] = data_frame[mean_column].mean()
        except Exception as e:
            results['mean_error'] = f"Error calculating mean: {str(e)}"

    # Calculate median if a column is selected for it
    if median_column:
        try:
            results['median'] = data_frame[median_column].median()
        except Exception as e:
            results['median_error'] = f"Error calculating median: {str(e)}"

    # Calculate mode if a column is selected for it
    if mode_column:
        try:
            results['mode'] = data_frame[mode_column].mode().iloc[0]
        except Exception as e:
            results['mode_error'] = f"Error calculating mode: {str(e)}"
    if std_column:
        std_result = data_frame[std_column].std()

        # Calculate variance if a column is selected
    if var_column:
        var_result= data_frame[var_column].var()
    if n > 0 and p > 0:
            # Calculate values for the binomial distribution
            x = np.arange(0, n+1)
            y = binom.pmf(x, n, p)
            
            # Plotting
            fig, ax = plt.subplots()
            ax.bar(x, y)
            ax.set_title('Binomial Distribution')
            ax.set_xlabel('Number of Successes')
            ax.set_ylabel('Probability')
            
            # Save plot to a buffer
            buf = BytesIO()
            plt.savefig(buf, format="png")
            plt.close(fig)
            bin_plot_data = base64.b64encode(buf.getvalue()).decode('utf-8')
            buf.close()
    if 0 <= pb <= 1:
            # Bernoulli distribution only needs the probability of success
            x = [0, 1]
            y = bernoulli.pmf(x, pb)
            
            # Plotting
            fig, ax = plt.subplots()
            ax.bar(x, y, tick_label=['Failure', 'Success'], color=['red', 'green'])
            ax.set_title('Bernoulli Distribution')
            ax.set_xlabel('Outcome')
            ax.set_ylabel('Probability')
            
            # Save the plot to a buffer
            buf = BytesIO()
            plt.savefig(buf, format="png")
            plt.close(fig)
            ber_plot_data = base64.b64encode(buf.getvalue()).decode('utf-8')
            buf.close()
    if mu>1 and sigma>1:
        x = np.linspace(mu - 3*sigma, mu + 3*sigma, 100)
        y = norm.pdf(x, mu, sigma)
        
        # Plotting
        fig, ax = plt.subplots()
        ax.plot(x, y)
        ax.set_title('Normal Distribution')
        ax.set_xlabel('Data Points')
        ax.set_ylabel('Probability Density')
        
        # Save the plot to a buffer
        buf = BytesIO()
        plt.savefig(buf, format="png")
        plt.close(fig)
        norm_plot_data = base64.b64encode(buf.getvalue()).decode('utf-8')
        buf.close()
        
    if lambda_value>0:
        
        # Generate data for the Poisson distribution
        x = np.arange(0, 50, 1)  # Generate up to 20 events
        y = poisson.pmf(x, lambda_value)
        
        # Plotting
        fig, ax = plt.subplots()
        ax.bar(x, y)
        ax.set_title('Poisson Distribution')
        ax.set_xlabel('Number of Events')
        ax.set_ylabel('Probability Mass')
        
        # Save the plot to a buffer
        buf = BytesIO()
        plt.savefig(buf, format="png")
        plt.close(fig)
        poi_plot_data = base64.b64encode(buf.getvalue()).decode('utf-8')
        buf.close()
    if b > a:
        
        # Generate data for the uniform distribution
        data = np.random.uniform(a, b, 1000)
            
        # Plotting
        fig, ax = plt.subplots()
        ax.hist(data, bins=30, density=True, alpha=0.75, color='blue')
        ax.set_title('Uniform Distribution')
        ax.set_xlabel('Value')
        ax.set_ylabel('Frequency')
            
        # Save the plot to a buffer
        buf = BytesIO()
        plt.savefig(buf, format="png")
        plt.close(fig)
        uni_plot_data = base64.b64encode(buf.getvalue()).decode('utf-8')
        buf.close()
        
    if rate > 0:
        
        # Generate data for the exponential distribution
        x = np.linspace(0, 10 / rate, 1000)
        y = expon.pdf(x, scale=1/rate)
            
        # Plotting
        fig, ax = plt.subplots()
        ax.plot(x, y)
        ax.set_title('Exponential Distribution')
        ax.set_xlabel('Data Points')
        ax.set_ylabel('Probability Density')
            
        # Save the plot to a buffer
        buf = BytesIO()
        plt.savefig(buf, format="png")
        plt.close(fig)
        exp_plot_data = base64.b64encode(buf.getvalue()).decode('utf-8')
        buf.close()
        
        
    return render(request, 'prob_file.html', {
        'file_name': user_file.name,
        'file_id': user_file.id,
        'file_id': user_file.id,
        'mean_column': mean_column,
        'median_column': median_column,
        'mode_column': mode_column,
        'quantitative': quantitative,
        'mode': mode,
        'results': results,
        'var_result': var_result,
        'std_result': std_result,
        'std_column': std_column,
        'var_column': var_column,
        'ran_column': ran_column,
        'range_result': range_result,
        'bin_plot_data': bin_plot_data,
        'ber_plot_data': ber_plot_data,
        'norm_plot_data': norm_plot_data,
        'poi_plot_data': poi_plot_data,
        'uni_plot_data': uni_plot_data,
        'exp_plot_data': exp_plot_data,
    })
