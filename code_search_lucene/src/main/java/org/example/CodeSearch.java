package org.example;

import org.apache.lucene.analysis.Analyzer;
import org.apache.lucene.analysis.standard.StandardAnalyzer;
import org.apache.lucene.document.*;
import org.apache.lucene.index.*;

import org.apache.lucene.queryparser.classic.ParseException;
import org.apache.lucene.queryparser.classic.QueryParser;
import org.apache.lucene.search.*;
import org.apache.lucene.store.Directory;
import org.apache.lucene.store.FSDirectory;
import org.json.JSONArray;
import org.json.JSONObject;

import javax.swing.text.html.parser.Parser;
import java.io.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.sql.*;
import java.util.ArrayList;
import java.util.List;


public class CodeSearch
{
    public static String escapeQueryChars(String s) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            // These characters are part of the query syntax and must be escaped
            switch (c) {
                case '\\':
                case '+':
                case '-':
                case '!':
                case '(':
                case ')':
                case ':':
                case '^':
                case '[':
                case ']':
                case '\"':
                case '{':
                case '}':
                case '~':
                case '*':
                case '?':
                case '|':
                case '&':
                case '/':
                    sb.append('\\');
                default:
                    sb.append(c);
            }
        }
        return sb.toString();
    }

    public static void write_index(Directory index, IndexWriterConfig config) throws SQLException, IOException {
        IndexWriter iwriter = new IndexWriter(index, config);
        Connection conn = DriverManager.getConnection("jdbc:sqlite:codebase_py.db");
        Statement stmt = conn.createStatement();
        ResultSet rs = stmt.executeQuery(
                "SELECT idx, code, code_tokens, comment, modified_comment, repo, is_valid FROM codebase;");
//         write the index
        while (rs.next()){
            Document doc = new Document();
            doc.add(new IntField("idx", rs.getInt("idx"), Field.Store.YES));
            doc.add(new StringField("repo", rs.getString("repo"), Field.Store.YES));
            doc.add(new TextField("code", rs.getString("code"), Field.Store.YES));
            doc.add(new TextField("code_tokens", rs.getString("code_tokens"), Field.Store.YES));
            doc.add(new TextField("comment", rs.getString("comment"), Field.Store.YES));
            doc.add(new TextField("modified_comment", rs.getString("modified_comment"), Field.Store.YES));
            doc.add(new IntField("is_valid", rs.getInt("is_valid"), Field.Store.YES));
            iwriter.addDocument(doc);
        }


        System.out.println("Document Done!");

        iwriter.close();
        rs.close();
        stmt.close();
        conn.close();
    }

    public static void initialize_store_file(String option, String order) throws FileNotFoundException {
        PrintWriter writer = new PrintWriter(option + ".txt_" + order);
        writer.print("");
        writer.close();
    }

    public static void store_result(List<List<JSONObject>> jsonList, Integer pid, String prompt, Boolean repo_flag, String option, String order) throws IOException {
        JSONObject JsonObject = new JSONObject();
        JsonObject.put("pid", pid);
        JsonObject.put("prompt", prompt);
        JsonObject.put("search_result", jsonList);
        System.out.println(JsonObject.toString(4));
        if (repo_flag) {
            FileWriter file = new FileWriter(option + "_repo.txt", true);
            file.write(JsonObject.toString());
            file.write(System.lineSeparator());
            file.flush();
        } else {
            FileWriter file = new FileWriter(option + ".txt_" + order, true);
            file.write(JsonObject.toString());
            file.write(System.lineSeparator());
            file.flush();
        }
    }

    public static String initialize_target_field(String option){
        String target_field;
        if (option.equals("all2code")) {
            target_field = "code_tokens";
        } else if (option.equals("code2code")) {
            target_field = "code_tokens";
        } else if (option.equals("text2text")) {
            target_field = "modified_comment";
        } else if (option.equals("text2code")) {
            target_field = "code_tokens";
        } else if (option.equals("error2code")) {
            target_field = "code_tokens";
        } else if (option.equals("query2code")) {
            target_field = "code_tokens";
        } else {
            target_field = "";
        }
        return target_field;
    }

    public static TopDocs query_index(Analyzer analyzer, Directory index, String prompt, String target_field) throws ParseException, IOException {
        List<JSONObject> jsonList = new ArrayList<>();
        if (prompt.isEmpty()){
            TopDocs results = null;
            return results;
        } else{
            String library = "";
            QueryParser parser = new QueryParser(target_field, analyzer);
            Query query = parser.parse(escapeQueryChars(prompt));

            IndexReader ireader = DirectoryReader.open(index);
            IndexSearcher isearcher = new IndexSearcher(ireader);
            TopDocs results;
            results = isearcher.search(query, 10);
            return results;
            }
    }

    public static void main( String[] args ) throws IOException, SQLException, ParseException {

        String option = "query2code";
        Boolean repo_flag = false;
        String order = "initial";
        initialize_store_file(option, order);
        String target_field = initialize_target_field(option);

        Analyzer analyzer = new StandardAnalyzer();

        Directory index = FSDirectory.open(Paths.get("index"));

        IndexWriterConfig config = new IndexWriterConfig(analyzer);
        System.out.println("Indexing Done!");


        BufferedReader br = new BufferedReader(new FileReader("error_res_list.json_" + order));


        TopDocs results;
        String line;
        IndexReader ireader = DirectoryReader.open(index);
        IndexSearcher isearcher = new IndexSearcher(ireader);

        while((line=br.readLine())!=null) {
            JSONObject jsonObject = new JSONObject(line);
            String prompt = "";
            Integer pid = jsonObject.getInt("pid");
            String library = "";



            if (option.equals("all2code")) {
                if (jsonObject.has("prompt")) {
                    prompt = jsonObject.getString("prompt");
                }
            } else if (option.equals("code2code")) {
                if (jsonObject.has("prompt_code")) {
                    prompt = jsonObject.getString("prompt_code");
                }
            } else if (option.equals("text2text")) {
                if (jsonObject.has("prompt_text")) {
                    prompt = jsonObject.getString("prompt_text");
                }
            } else if (option.equals("text2code")) {
                if (jsonObject.has("prompt_text")) {
                    prompt = jsonObject.getString("prompt_text");
                }
            }  else if (option.equals("error2code")) {
                if (jsonObject.has("error_line")) {
                    Object errorLineValue = jsonObject.get("error_line");
                    if (errorLineValue instanceof String) {
                        prompt = (String) errorLineValue;
                        if (prompt.isEmpty()) {
                            prompt = jsonObject.getString("generated_code");
                        }
                    }
                }
            } else if (option.equals("query2code")){
                if (jsonObject.has("query")) {
                    List<List<JSONObject>> jsonList = new ArrayList<>();
                    JSONArray jsonArray = jsonObject.getJSONArray("query");

                    for (int i = 0; i < jsonArray.length(); i++) {
                        prompt = jsonArray.getString(i);
                        results = query_index(analyzer, index, prompt, target_field);

                        System.out.println("index: " + pid + ", Library: " + library);
                        System.out.println("Total Hits: " + results.totalHits);

                        List<JSONObject> query_jsonList = new ArrayList<>();
                        for (ScoreDoc scoreDoc : results.scoreDocs) {
                            Document doc = isearcher.doc(scoreDoc.doc);

                            JSONObject tmp_JsonObject = new JSONObject();
                            tmp_JsonObject.put("idx", Integer.valueOf(doc.get("idx")));
                            tmp_JsonObject.put("score", scoreDoc.score);
                            query_jsonList.add(tmp_JsonObject);

                        }
                        jsonList.add(query_jsonList);
                    }
                    store_result(jsonList, pid, prompt, repo_flag, option, order);
                }

            } else {
                prompt = jsonObject.getString("generated_code");
            }
        }

    }
}
