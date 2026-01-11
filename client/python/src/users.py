from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional
from enum import Enum
import uuid
from neo4j import GraphDatabase, Driver, Result
from neo4j.graph import Node
from neo4j.time import Date

class Gender(Enum):
    """ユーザの性別

    Attributes:
        MALE: 男性
        FEMALE: 女性
        OTHER: その他
    """
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class User:
    """Userノード

    Attributes:
        properties (Optional[User._Properties]): ユーザのプロパティ情報
    """
    properties: Optional[User._Properties]

    def __init__(self, user_id: str, name: str, birth_date: Optional[date] = None, gender: Optional[Gender] = None):
        self.properties = User._Properties(
            user_id=user_id,
            name=name,
            birth_date=birth_date,
            gender=gender
        )

    @dataclass
    class _Properties:
        """Userノードのプロパティ

        Attributes:
            user_id (str): ユーザID
            name (str): ユーザ名
            birth_date (Optional[date]): 生年月日
            gender (Optional[Gender]): 性別
        """
        user_id: str
        name: str
        birth_date: Optional[date] = None
        gender: Optional[Gender] = None

        def to_dict(self) -> dict:
            return {
                "user_id": self.user_id,
                "name": self.name,
                "birth_date": self.birth_date,
                "gender": self.gender.value if self.gender else None,
            }

    def to_dict(self) -> dict:
        return {
            "properties": self.properties.to_dict() if self.properties else None
        }

    @staticmethod
    def from_entity(node: Node):
        properties: dict = dict(node)
        birth_date: Date | None = properties.get("birth_date")
        gender = properties.get("gender")

        return User(
            user_id=properties.get("user_id"),
            name=properties.get("name"),
            birth_date=birth_date.to_native() if isinstance(birth_date, Date) else None,
            gender=Gender(gender) if gender else None
        )

class FollowRelationship:
    """FOLLOWSリレーションシップ

    Attributes:
        start_node (User): フォローする側のユーザ
        end_node (User): フォローされる側のユーザ
        properties (Optional[FollowRelationship._Properties]): リレーションシップのプロパティ情報
    """
    start_node: User
    end_node: User
    properties: Optional[FollowRelationship._Properties]

    def __init__(self, relationship_id: str, start_node: User, end_node: User, since: datetime):
        self.start_node = start_node
        self.end_node = end_node
        self.properties = FollowRelationship._Properties(
            relationship_id=relationship_id,
            since=since
        )

    @dataclass
    class _Properties:
        """FOLLOWSリレーションシップのプロパティ

        Attributes:
            relationship_id (str): リレーションシップID
            since (datetime): フォロー開始日時
        """
        relationship_id: str
        since: datetime

        def to_dict(self) -> dict:
            return {
                "relationship_id": self.relationship_id,
                "since": self.since,
            }

    def to_dict(self) -> dict:
        return {
            "start_user_id": self.start_node.properties.user_id,
            "end_user_id": self.end_node.properties.user_id,
            "properties": self.properties.to_dict() if self.properties else None
        }

    @staticmethod
    def from_entity(relationship, start_node: User, end_node: User):
        properties: dict = dict(relationship)
        return FollowRelationship(
            relationship_id=properties.get("relationship_id"),
            start_node=start_node,
            end_node=end_node,
            since=properties.get("since")
        )

def create_user_nodes(driver: Driver, users: list[User]) -> list[User]:
    # Neo4j セッション作成
    with driver.session() as session:
        # ユーザのプロパティ一覧を作成
        users_dict: list[dict] = [user.to_dict() for user in users]

        # クエリを作成
        query: str = """
        UNWIND $users AS user
        CREATE (u:User)
        Set u = user.properties
        return u
        """

        # クエリを実行
        result: Result = session.run(query=query, users=users_dict)
        created_users = []
        for record in result:
            user_node: Node = record["u"]
            created_users.append(User.from_entity(user_node))

        return created_users

def create_follow_relationships(driver: Driver, follow_relationships: list[FollowRelationship]) -> list[FollowRelationship]:
    # Neo4j セッション作成
    with driver.session() as session:

        # リレーションシップのプロパティ一覧を作成
        relationships_dict: list[dict] = [rel.to_dict() for rel in follow_relationships]

        query: str = """
        UNWIND $follow_relationships AS follow
        MATCH (start:User {user_id: follow.start_user_id})
        MATCH (end:User {user_id: follow.end_user_id})
        CREATE (start) -[f:FOLLOWS]-> (end)
        SET f = follow.properties
        RETURN f, start, end
        """

        # クエリを実行
        result: Result = session.run(query=query, follow_relationships=relationships_dict)
        created_relationships = []
        for record in result:
            follow_relationship = record["f"]
            start_node = record["start"]
            end_node = record["end"]
            created_relationships.append(
                FollowRelationship.from_entity(
                    follow_relationship,
                    User.from_entity(start_node),
                    User.from_entity(end_node)
                )
            )

        return created_relationships

def main():
    try:
        with GraphDatabase.driver("bolt://neo4j:7687") as driver:
            # 登録するユーザを作成
            users: list[User] = []
            users.append(User(
                user_id=str(uuid.uuid4()),
                name="Alice"))
            users.append(User(
                user_id=str(uuid.uuid4()),
                name="Bob",
                birth_date=date(1990, 1, 2)))
            users.append(User(
                user_id=str(uuid.uuid4()),
                name="Charlie",
                birth_date=date(2000, 10, 11),
                gender=Gender.FEMALE))

            # Userノードを作成
            created_users: list[User] = create_user_nodes(driver, users)

            # 登録するリレーションを作成
            follow_relationships: list[FollowRelationship] = []
            # 0 -> 1
            follow_relationships.append(FollowRelationship(
                relationship_id=str(uuid.uuid4()),
                start_node=created_users[0],
                end_node=created_users[1],
                since=datetime(2024, 1, 2)))
            # 1 -> 2
            follow_relationships.append(FollowRelationship(
                relationship_id=str(uuid.uuid4()),
                start_node=created_users[1],
                end_node=created_users[2],
                since=datetime(2025, 3, 4)))
            # 2 -> 1
            follow_relationships.append(FollowRelationship(
                relationship_id=str(uuid.uuid4()),
                start_node=created_users[2],
                end_node=created_users[1],
                since=datetime(2026, 5, 6)))

            # Followリレーションシップを作成
            created_relationships = create_follow_relationships(driver, follow_relationships)

    except Exception as e:
        print(e)

if __name__=="__main__":
    main()
