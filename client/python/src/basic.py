from neo4j import GraphDatabase, Driver, Session, Result, ResultSummary

def main():
    # セッション作成
    driver: Driver = GraphDatabase.driver("bolt://neo4j:7687")
    session: Session = driver.session()

    # nodeを1つ作成
    result_create: Result = session.run("CREATE (n)")
    summary_create: ResultSummary = result_create.consume()
    print(summary_create.counters)

    # 作成したnodeを取得
    result_match: Result = session.run("MATCH (n) RETURN n")
    print(list(result_match))

    # nodeをすべて削除
    result_delete: Result = session.run("MATCH (n) DETACH DELETE n")
    summary_delete: ResultSummary = result_delete.consume()
    print(summary_delete.counters)

    # セッション破棄
    session.close()
    driver.close()

if __name__ == "__main__":
    main()