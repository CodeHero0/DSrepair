# Knowledge-Enhanced Program Repair for Data Science Code

## Figures
We add equivalent Venn diagrams for Figure 5 and Figure 'API_knowledge_example.pdf' under path 'fig/'.

## Datasets
[DS-1000](https://github.com/xlang-ai/DS-1000) 
You can download the DS-1000 dataset from [huggingface](https://huggingface.co/datasets/xlangai/DS-1000).
For the details of this dataset, you can see their [github page](https://github.com/xlang-ai/DS-1000)

## API documents

The online document versions of each library we used in this study are shown as follows:
- [Numpy](https://numpy.org/doc/): 1.26
- [Pandas](https://pandas.pydata.org/pandas-docs/stable/): 2.2.0
- [SciPy](https://docs.scipy.org/doc/scipy/index.html): 1.12.0
- [Scikit-learn](https://scikit-learn.org/dev/versions.html): 1.4.1
- [Matplotlib](https://github.com/matplotlib/matplotlib/tree/main/doc): 3.8.2
- [PyTorch](https://github.com/pytorch/pytorch/tree/main/docs): 2.2.0
- [TensorFlow](https://github.com/tensorflow/tensorflow): 2.16.0

The API documents are public assessed online.

## Knowledge Graph Server
[Apache Jena Fuseki](https://jena.apache.org/documentation/fuseki2/) 

We use the Fuseki server to assist with triple storage and retrieval with KG.
Go to the webpage, you can download the jena-fuseki-server with different versions.
In our work, we use the latest version.

## Tools

### Code Search

We use [Lucene](https://lucene.apache.org/) to support our code search with code base PyTorrent, which can be downloaded from [here](https://zenodo.org/records/4546290).
The code of the code search is shown in the folder `code_search_lucene`.
Due to the insufficient support of Lucene in Python, we provide the code search logic written in Java.

### Knowledge Retrieval

We design an ontology for our DS-KG (Data Science Knowledge Graph) in `knowledge_graph/ontology.ttl`.
The code of how to construct DS-KG for different libraries is shown in `knowledge_graph/kg_construction_*.py`
All the `knowledge_graph/kg_construction_*.py` is powered by `kg_api.py`, which requires the user to set up the Fuseki server first.
The overall DS-KG is stored in `knowledge_graph/DS-KG.ttl`.

#### !!!!!!!!!!!!NEW!!!!!!!!!!!!!!!!!!
In the `knowledge_graph/ontology.ttl`, we mainly defined the following owlClass, namely, Library, Module, Function, Parameter, and Return.
We also defined some owlObjectProperty, between the owlClass, i.e., 'hasFunction', 'hasParameter', and 'belongsToLibrary'.
For each API function, we define some owlDatatypeProperty, i.e., 'hasExplanation', 'hasExpression', and 'hasNote', which can cover the majority of information in its corresponding API document's webpage.

The visualization website: [WebVOWL](https://service.tib.eu/webvowl/)
1. Go the bottom sidebar, select 'Ontology'
2. In the Custom Ontology, choose 'select ontology file'
3. Upload the `knowledge_graph/ontology.ttl` file, then you can visualize the ontology.


### Plain Text Search

We collect all the plain text content for all online API documents and store them in `knowledge_graph/plain_text.json`.


## Code
Our experiments mainly contain the following main files:

### Code Generation
We use `code_generate.py` to generate the initial response from LLM, and store them into JSON files in `./intermediat_result/first_test`.
This folder contains an example intermediate_result after the test.

### Code Test
We use `code_test.py` to test the generated code with the test cases given in the dataset.

### Code Repair
We use `code_repair.py` to repair the buggy code with our DSrepair approach.
Inside the file, you can change the prompt engineering strategies by modifying the last line of the code.
Our code repair supports the following options: 'Code_Search', 'Chat_Repair', 'Self_Repair', 'Debugging_S', 'Debugging_E', and 'DSrepair'.

'Chat_Repair', 'Self_Repair', 'Debugging_S', and `Debugging_E' are fully LLM-based code repairs.
'Code_Search' needs to leverage Code Search in the code database.
'DSrepair' needs to leverage the DS-KG for knowledge retrieval.

For code generation and code repair, we need to leverage LLM. Therefore, before running the code, please make sure to fill in the KEY of different LLMs in folder `openai_info/`. The KEYs can be generated from their websites:
- [OpenAI](https://platform.openai.com/docs/models)
- [DeepSeek](https://www.deepseek.com/)
- [Mistral AI](https://mistral.ai/)

## Results
Our experiment results are stored in the folder `experiment_result`. There are different categories corresponding to different prompt engineering strategies.

Each specific result contains two files, one is the JSON file (e.g.`experiment_result/DSrepair/gpt_all/ds1000_model_gpt-3.5-turbo_fl_kg.json_0`) recording the response from LLMs; the other one inside folder `repair_test/' recording the evaluation result after testing from the test cases.

For the identical prompt, we ran the experiment three times to mitigate the inherent randomness of LLMs.

## Prompt

The detail of the prompt design can be found in `enrich_prompt.py`, and the example of the prompt can be found in `experiment_result`.

