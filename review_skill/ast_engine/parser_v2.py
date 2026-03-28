"""
AST Parser v2 - 真正的Kotlin语法树解析器 (修复版)

实现递归下降解析器，构建完整的抽象语法树。
处理真实Kotlin代码如PermissionManager.kt
"""

import re
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass, field
from enum import Enum, auto


class TokenType(Enum):
    """词法单元类型"""
    # 关键字
    PACKAGE = auto()
    IMPORT = auto()
    CLASS = auto()
    INTERFACE = auto()
    OBJECT = auto()
    COMPANION = auto()
    DATA = auto()
    SEALED = auto()
    ABSTRACT = auto()
    OPEN = auto()
    OVERRIDE = auto()
    PRIVATE = auto()
    PROTECTED = auto()
    PUBLIC = auto()
    INTERNAL = auto()
    FUN = auto()
    VAL = auto()
    VAR = auto()
    CONST = auto()
    LATEINIT = auto()
    SUSPEND = auto()
    INLINE = auto()
    RETURN = auto()
    IF = auto()
    ELSE = auto()
    WHEN = auto()
    FOR = auto()
    WHILE = auto()
    DO = auto()
    TRY = auto()
    CATCH = auto()
    FINALLY = auto()
    THROW = auto()
    THIS = auto()
    SUPER = auto()
    BY = auto()
    WHERE = auto()
    INIT = auto()
    GET = auto()
    SET = auto()
    FIELD = auto()
    
    # 标识符和字面量
    IDENTIFIER = auto()
    STRING_LITERAL = auto()
    INTEGER_LITERAL = auto()
    FLOAT_LITERAL = auto()
    BOOLEAN_LITERAL = auto()
    NULL_LITERAL = auto()
    
    # 运算符
    ARROW = auto()           # ->
    DOUBLE_ARROW = auto()    # =>
    RANGE = auto()           # ..
    ELLIPSIS = auto()        # ...
    EQ = auto()              # ==
    NE = auto()              # !=
    LE = auto()              # <=
    GE = auto()              # >=
    INCREMENT = auto()       # ++
    DECREMENT = auto()       # --
    AND = auto()             # &&
    OR = auto()              # ||
    SAFE_CALL = auto()       # ?.
    NOT_NULL = auto()        # !!
    
    # 单字符
    LPAREN = auto()          # (
    RPAREN = auto()          # )
    LBRACE = auto()          # {
    RBRACE = auto()          # }
    LBRACKET = auto()        # [
    RBRACKET = auto()        # ]
    LT = auto()              # <
    GT = auto()              # >
    ASSIGN = auto()          # =
    PLUS = auto()            # +
    MINUS = auto()           # -
    MULT = auto()            # *
    DIV = auto()             # /
    MOD = auto()             # %
    NOT = auto()             # !
    DOT = auto()             # .
    COMMA = auto()           # ,
    COLON = auto()           # :
    SEMICOLON = auto()       # ;
    QUESTION = auto()        # ?
    AT = auto()              # @
    HASH = auto()            # #
    DOLLAR = auto()          # $
    BACKTICK = auto()        # `
    
    # 特殊
    EOF = auto()


@dataclass
class Token:
    """词法单元"""
    type: TokenType
    value: str
    line: int
    column: int
    offset: int


class KotlinLexer:
    """Kotlin词法分析器 - 增强版"""
    
    KEYWORDS = {
        'package': TokenType.PACKAGE,
        'import': TokenType.IMPORT,
        'class': TokenType.CLASS,
        'interface': TokenType.INTERFACE,
        'object': TokenType.OBJECT,
        'companion': TokenType.COMPANION,
        'data': TokenType.DATA,
        'sealed': TokenType.SEALED,
        'abstract': TokenType.ABSTRACT,
        'open': TokenType.OPEN,
        'override': TokenType.OVERRIDE,
        'private': TokenType.PRIVATE,
        'protected': TokenType.PROTECTED,
        'public': TokenType.PUBLIC,
        'internal': TokenType.INTERNAL,
        'fun': TokenType.FUN,
        'val': TokenType.VAL,
        'var': TokenType.VAR,
        'const': TokenType.CONST,
        'lateinit': TokenType.LATEINIT,
        'suspend': TokenType.SUSPEND,
        'inline': TokenType.INLINE,
        'return': TokenType.RETURN,
        'if': TokenType.IF,
        'else': TokenType.ELSE,
        'when': TokenType.WHEN,
        'for': TokenType.FOR,
        'while': TokenType.WHILE,
        'do': TokenType.DO,
        'try': TokenType.TRY,
        'catch': TokenType.CATCH,
        'finally': TokenType.FINALLY,
        'throw': TokenType.THROW,
        'this': TokenType.THIS,
        'super': TokenType.SUPER,
        'by': TokenType.BY,
        'where': TokenType.WHERE,
        'init': TokenType.INIT,
        'get': TokenType.GET,
        'set': TokenType.SET,
        'field': TokenType.FIELD,
        'true': TokenType.BOOLEAN_LITERAL,
        'false': TokenType.BOOLEAN_LITERAL,
        'null': TokenType.NULL_LITERAL,
    }
    
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
    
    def tokenize(self) -> List[Token]:
        """词法分析"""
        while not self._is_at_end():
            self._scan_token()
        
        self.tokens.append(Token(TokenType.EOF, '', self.line, self.column, self.pos))
        return self.tokens
    
    def _is_at_end(self) -> bool:
        return self.pos >= len(self.source)
    
    def _peek(self, offset: int = 0) -> str:
        idx = self.pos + offset
        if idx >= len(self.source):
            return '\0'
        return self.source[idx]
    
    def _advance(self) -> str:
        char = self._peek()
        self.pos += 1
        if char == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char
    
    def _match(self, expected: str) -> bool:
        if self._is_at_end() or self._peek() != expected:
            return False
        self._advance()
        return True
    
    def _scan_token(self):
        """扫描单个词法单元"""
        start_line = self.line
        start_col = self.column
        start_pos = self.pos
        
        char = self._advance()
        
        # 跳过空白字符和注释
        if char in ' \t\r\n':
            return
        
        # 注释
        if char == '/' and self._peek() == '/':
            self._scan_line_comment()
            return
        if char == '/' and self._peek() == '*':
            self._scan_block_comment()
            return
        
        # 字符串
        if char == '"':
            if self._peek() == '"' and self._peek(1) == '"':
                self._scan_multiline_string()
            else:
                self._scan_string()
            return
        
        # 字符字面量
        if char == "'":
            self._scan_char_literal()
            return
        
        # 标识符
        if char.isalpha() or char == '_' or char == '`':
            self._scan_identifier(char, start_line, start_col, start_pos)
            return
        
        # 数字
        if char.isdigit():
            self._scan_number(char, start_line, start_col, start_pos)
            return
        
        # 多字符运算符
        two_char = char + self._peek()
        if two_char == '->':
            self._advance()
            self._add_token(TokenType.ARROW, '->', start_line, start_col, start_pos)
            return
        if two_char == '=>':
            self._advance()
            self._add_token(TokenType.DOUBLE_ARROW, '=>', start_line, start_col, start_pos)
            return
        if two_char == '..':
            self._advance()
            if self._peek() == '.':
                self._advance()
                self._add_token(TokenType.ELLIPSIS, '...', start_line, start_col, start_pos)
            else:
                self._add_token(TokenType.RANGE, '..', start_line, start_col, start_pos)
            return
        if two_char == '==':
            self._advance()
            self._add_token(TokenType.EQ, '==', start_line, start_col, start_pos)
            return
        if two_char == '!=':
            self._advance()
            self._add_token(TokenType.NE, '!=', start_line, start_col, start_pos)
            return
        if two_char == '<=':
            self._advance()
            self._add_token(TokenType.LE, '<=', start_line, start_col, start_pos)
            return
        if two_char == '>=':
            self._advance()
            self._add_token(TokenType.GE, '>=', start_line, start_col, start_pos)
            return
        if two_char == '++':
            self._advance()
            self._add_token(TokenType.INCREMENT, '++', start_line, start_col, start_pos)
            return
        if two_char == '--':
            self._advance()
            self._add_token(TokenType.DECREMENT, '--', start_line, start_col, start_pos)
            return
        if two_char == '&&':
            self._advance()
            self._add_token(TokenType.AND, '&&', start_line, start_col, start_pos)
            return
        if two_char == '||':
            self._advance()
            self._add_token(TokenType.OR, '||', start_line, start_col, start_pos)
            return
        if two_char == '?.':
            self._advance()
            self._add_token(TokenType.SAFE_CALL, '?.', start_line, start_col, start_pos)
            return
        if two_char == '!!':
            self._advance()
            self._add_token(TokenType.NOT_NULL, '!!', start_line, start_col, start_pos)
            return
        
        # 单字符
        single_char_tokens = {
            '(': TokenType.LPAREN, ')': TokenType.RPAREN,
            '{': TokenType.LBRACE, '}': TokenType.RBRACE,
            '[': TokenType.LBRACKET, ']': TokenType.RBRACKET,
            '<': TokenType.LT, '>': TokenType.GT,
            '=': TokenType.ASSIGN, '+': TokenType.PLUS,
            '-': TokenType.MINUS, '*': TokenType.MULT,
            '/': TokenType.DIV, '%': TokenType.MOD,
            '!': TokenType.NOT, '.': TokenType.DOT,
            ',': TokenType.COMMA, ':': TokenType.COLON,
            ';': TokenType.SEMICOLON, '?': TokenType.QUESTION,
            '@': TokenType.AT, '#': TokenType.HASH,
            '$': TokenType.DOLLAR, '`': TokenType.BACKTICK,
        }
        
        if char in single_char_tokens:
            self._add_token(single_char_tokens[char], char, start_line, start_col, start_pos)
    
    def _scan_line_comment(self):
        """扫描行注释"""
        while self._peek() != '\n' and not self._is_at_end():
            self._advance()
    
    def _scan_block_comment(self):
        """扫描块注释"""
        self._advance()  # skip *
        depth = 1
        while depth > 0 and not self._is_at_end():
            if self._peek() == '/' and self._peek(1) == '*':
                self._advance()
                self._advance()
                depth += 1
            elif self._peek() == '*' and self._peek(1) == '/':
                self._advance()
                self._advance()
                depth -= 1
            else:
                self._advance()
    
    def _scan_string(self):
        """扫描字符串"""
        while self._peek() != '"' and not self._is_at_end():
            if self._peek() == '\\':
                self._advance()
            self._advance()
        if not self._is_at_end():
            self._advance()  # closing "
    
    def _scan_multiline_string(self):
        """扫描多行字符串"""
        self._advance()
        self._advance()  # skip """
        while not (self._peek() == '"' and self._peek(1) == '"' and self._peek(2) == '"') and not self._is_at_end():
            self._advance()
        if not self._is_at_end():
            self._advance()
            self._advance()
            self._advance()  # closing """
    
    def _scan_char_literal(self):
        """扫描字符字面量"""
        while self._peek() != "'" and not self._is_at_end():
            if self._peek() == '\\':
                self._advance()
            self._advance()
        if not self._is_at_end():
            self._advance()  # closing '
    
    def _scan_identifier(self, first_char: str, line: int, col: int, pos: int):
        """扫描标识符"""
        value = first_char
        
        if first_char == '`':
            # 反引号包裹的标识符
            while self._peek() != '`' and not self._is_at_end():
                value += self._advance()
            if not self._is_at_end():
                value += self._advance()  # closing `
        else:
            while self._peek().isalnum() or self._peek() == '_':
                value += self._advance()
        
        # 检查是否是关键字
        token_type = self.KEYWORDS.get(value, TokenType.IDENTIFIER)
        self._add_token(token_type, value, line, col, pos)
    
    def _scan_number(self, first_char: str, line: int, col: int, pos: int):
        """扫描数字"""
        value = first_char
        is_float = False
        
        while self._peek().isdigit():
            value += self._advance()
        
        if self._peek() == '.' and self._peek(1).isdigit():
            is_float = True
            value += self._advance()
            while self._peek().isdigit():
                value += self._advance()
        
        # 科学计数法
        if self._peek().lower() == 'e':
            is_float = True
            value += self._advance()
            if self._peek() in '+-':
                value += self._advance()
            while self._peek().isdigit():
                value += self._advance()
        
        # 后缀
        if self._peek().lower() in 'ulf':
            value += self._advance()
        
        token_type = TokenType.FLOAT_LITERAL if is_float else TokenType.INTEGER_LITERAL
        self._add_token(token_type, value, line, col, pos)
    
    def _add_token(self, token_type: TokenType, value: str, line: int, col: int, pos: int):
        """添加词法单元"""
        self.tokens.append(Token(token_type, value, line, col, pos))


# ==================== 语法分析器 ====================

from .nodes import ASTNode, NodeType, Position, SourceRange


class ParseError(Exception):
    """解析错误"""
    pass


class KotlinParser:
    """Kotlin语法分析器 - 增强版，处理真实代码"""
    
    MODIFIER_KEYWORDS = [
        'public', 'private', 'protected', 'internal',
        'abstract', 'open', 'override', 'final', 'sealed',
        'const', 'lateinit', 'suspend', 'inline', 'crossinline', 'noinline',
        'external', 'operator', 'infix', 'tailrec', 'data',
        'inner', 'annotation', 'companion', 'enum', 'expect', 'actual'
    ]
    
    def __init__(self, tokens: List[Token], source: str):
        self.tokens = tokens
        self.source = source
        self.pos = 0
    
    def _peek(self, offset: int = 0) -> Token:
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[idx]
    
    def _advance(self) -> Token:
        token = self._peek()
        if not self._is_at_end():
            self.pos += 1
        return token
    
    def _is_at_end(self) -> bool:
        return self._peek().type == TokenType.EOF
    
    def _match(self, *types: TokenType) -> bool:
        for token_type in types:
            if self._check(token_type):
                self._advance()
                return True
        return False
    
    def _check(self, token_type: TokenType) -> bool:
        if self._is_at_end():
            return False
        return self._peek().type == token_type
    
    def _get_source_position(self, token: Token) -> Position:
        """将token位置转换为源码位置"""
        return Position(line=token.line - 1, column=token.column - 1, offset=token.offset)
    
    def parse(self) -> ASTNode:
        """解析Kotlin文件"""
        children = []
        start_token = self._peek()
        
        # 可选的包声明
        if self._check(TokenType.PACKAGE):
            children.append(self._parse_package())
        
        # 导入列表
        while self._check(TokenType.IMPORT):
            children.append(self._parse_import())
        
        # 顶层声明
        while not self._is_at_end():
            decl = self._parse_top_level_declaration()
            if decl:
                children.append(decl)
        
        # 创建文件节点
        last_token = self._peek(-1) if self.pos > 0 else start_token
        start_pos = self._get_source_position(start_token)
        end_pos = self._get_source_position(last_token)
        end_pos.offset += len(last_token.value)
        end_pos.column += len(last_token.value)
        
        return ASTNode(
            node_type=NodeType.FILE,
            text=self.source,
            range=SourceRange(start=start_pos, end=end_pos),
            children=children
        )
    
    def _parse_package(self) -> ASTNode:
        """解析包声明"""
        start_token = self._advance()  # package
        start_pos = self._get_source_position(start_token)
        
        # 解析包名
        name_parts = []
        while self._check(TokenType.IDENTIFIER):
            name_parts.append(self._advance().value)
            if not self._match(TokenType.DOT):
                break
        
        end_token = self._peek(-1)
        end_pos = self._get_source_position(end_token)
        end_pos.offset += len(end_token.value)
        end_pos.column += len(end_token.value)
        
        return ASTNode(
            node_type=NodeType.PACKAGE_HEADER,
            text=f"package {'.'.join(name_parts)}",
            range=SourceRange(start=start_pos, end=end_pos),
            children=[],
            metadata={'package_name': '.'.join(name_parts)}
        )
    
    def _parse_import(self) -> ASTNode:
        """解析导入声明"""
        start_token = self._advance()  # import
        start_pos = self._get_source_position(start_token)
        
        # 解析导入路径
        path_parts = []
        while self._check(TokenType.IDENTIFIER) or self._check(TokenType.MULT):
            path_parts.append(self._advance().value)
            if not self._match(TokenType.DOT):
                break
        
        # as 别名
        alias = None
        if self._peek().value == 'as':
            self._advance()  # as
            if self._check(TokenType.IDENTIFIER):
                alias = self._advance().value
        
        end_token = self._peek(-1)
        end_pos = self._get_source_position(end_token)
        end_pos.offset += len(end_token.value)
        end_pos.column += len(end_token.value)
        
        return ASTNode(
            node_type=NodeType.IMPORT_HEADER,
            text=f"import {'.'.join(path_parts)}",
            range=SourceRange(start=start_pos, end=end_pos),
            children=[],
            metadata={'import_path': '.'.join(path_parts), 'alias': alias}
        )
    
    def _parse_top_level_declaration(self) -> Optional[ASTNode]:
        """解析顶层声明"""
        # 跳过注解和修饰符，获取实际声明类型
        saved_pos = self.pos
        
        # 解析注解
        annotations = self._parse_annotations()
        
        # 解析修饰符
        modifiers = self._parse_modifiers()
        
        # 根据关键字判断声明类型
        if self._check(TokenType.CLASS) or self._check(TokenType.INTERFACE):
            return self._parse_class_declaration(modifiers, annotations)
        elif self._check(TokenType.OBJECT):
            return self._parse_object_declaration(modifiers, annotations)
        elif self._check(TokenType.FUN):
            return self._parse_function_declaration(modifiers, annotations)
        elif self._check(TokenType.VAL) or self._check(TokenType.VAR):
            return self._parse_property_declaration(modifiers, annotations)
        
        # 无法识别，恢复位置并跳过
        self.pos = saved_pos
        if not self._is_at_end():
            self._advance()
        return None
    
    def _parse_annotations(self) -> List[ASTNode]:
        """解析注解"""
        annotations = []
        while self._match(TokenType.AT):
            # 解析注解名
            if self._check(TokenType.IDENTIFIER):
                self._advance()
                # 跳过参数
                if self._match(TokenType.LPAREN):
                    self._skip_balanced('(', ')')
            # 文件级注解
            elif self._match(TokenType.COLON):
                if self._check(TokenType.IDENTIFIER):
                    self._advance()
        return annotations
    
    def _parse_modifiers(self) -> List[str]:
        """解析修饰符"""
        modifiers = []
        modifier_token_types = [
            TokenType.ABSTRACT, TokenType.OPEN, TokenType.OVERRIDE,
            TokenType.DATA, TokenType.SEALED, TokenType.CONST,
            TokenType.LATEINIT, TokenType.SUSPEND, TokenType.INLINE,
            TokenType.PRIVATE, TokenType.PROTECTED, TokenType.PUBLIC, TokenType.INTERNAL,
        ]
        
        while True:
            if any(self._check(t) for t in modifier_token_types):
                modifiers.append(self._advance().value)
            elif self._check(TokenType.IDENTIFIER) and self._peek().value in self.MODIFIER_KEYWORDS:
                modifiers.append(self._advance().value)
            else:
                break
        return modifiers
    
    def _parse_class_declaration(self, modifiers: List[str], annotations: List[ASTNode]) -> ASTNode:
        """解析类声明"""
        start_token = self._advance()  # class/interface
        start_pos = self._get_source_position(start_token)
        
        is_interface = start_token.type == TokenType.INTERFACE
        
        # 类名
        class_name = ""
        if self._check(TokenType.IDENTIFIER):
            class_name = self._advance().value
        
        # 类型参数
        if self._match(TokenType.LT):
            self._skip_type_parameters()
        
        # 主构造函数
        if self._check(TokenType.LPAREN):
            self._skip_balanced('(', ')')
        
        # 继承
        if self._match(TokenType.COLON):
            self._skip_super_types()
        
        # where子句
        if self._check(TokenType.WHERE):
            self._skip_where_clause()
        
        # 类体
        body = None
        if self._check(TokenType.LBRACE):
            body = self._parse_class_body()
        
        end_token = self._peek(-1)
        end_pos = self._get_source_position(end_token)
        end_pos.offset += len(end_token.value)
        end_pos.column += len(end_token.value)
        
        node_type = NodeType.INTERFACE_DECLARATION if is_interface else NodeType.CLASS_DECLARATION
        
        return ASTNode(
            node_type=node_type,
            text=f"{start_token.value} {class_name}",
            range=SourceRange(start=start_pos, end=end_pos),
            children=body or [],
            metadata={
                'class_name': class_name,
                'is_interface': is_interface,
                'modifiers': modifiers
            }
        )
    
    def _parse_object_declaration(self, modifiers: List[str], annotations: List[ASTNode]) -> ASTNode:
        """解析对象声明"""
        start_token = self._advance()  # object or companion
        start_pos = self._get_source_position(start_token)
        
        is_companion = False
        if start_token.type == TokenType.COMPANION:
            is_companion = True
            self._match(TokenType.OBJECT)  # 可选的object关键字
        
        # 对象名（可选，companion object可能没有名字）
        object_name = ""
        if self._check(TokenType.IDENTIFIER):
            object_name = self._advance().value
        
        # 继承
        if self._match(TokenType.COLON):
            self._skip_super_types()
        
        # 类体
        body = None
        if self._check(TokenType.LBRACE):
            body = self._parse_class_body()
        
        end_token = self._peek(-1)
        end_pos = self._get_source_position(end_token)
        end_pos.offset += len(end_token.value)
        end_pos.column += len(end_token.value)
        
        node_type = NodeType.COMPANION_OBJECT if is_companion else NodeType.OBJECT_DECLARATION
        
        return ASTNode(
            node_type=node_type,
            text=f"{start_token.value} {object_name}".strip(),
            range=SourceRange(start=start_pos, end=end_pos),
            children=body or [],
            metadata={
                'object_name': object_name,
                'is_companion': is_companion,
                'modifiers': modifiers
            }
        )
    
    def _parse_function_declaration(self, modifiers: List[str], annotations: List[ASTNode]) -> ASTNode:
        """解析函数声明 - 修复版"""
        start_token = self._advance()  # fun
        start_pos = self._get_source_position(start_token)
        
        # 类型参数
        if self._match(TokenType.LT):
            self._skip_type_parameters()
        
        # 函数名（支持扩展函数如 PermissionManager.getInstance）
        function_name = ""
        while True:
            if self._check(TokenType.IDENTIFIER):
                function_name = self._advance().value
            elif self._check(TokenType.BACKTICK):  # 反引号包裹的函数名
                self._advance()
                if self._check(TokenType.IDENTIFIER):
                    function_name = self._advance().value
                if self._check(TokenType.BACKTICK):
                    self._advance()
            
            # 检查是否是扩展函数（ReceiverType.functionName）
            if self._match(TokenType.DOT):
                # 继续解析真正的函数名
                continue
            break
        
        # 参数列表（可选）
        if self._check(TokenType.LPAREN):
            self._advance()  # consume (
            self._skip_value_parameters()
        
        # 返回类型
        if self._match(TokenType.COLON):
            self._skip_type()
        
        # where子句
        if self._check(TokenType.WHERE):
            self._skip_where_clause()
        
        # 函数体
        body = None
        if self._check(TokenType.LBRACE):
            body = self._parse_block()
        elif self._match(TokenType.ASSIGN):
            # 表达式体
            self._skip_expression()
        
        end_token = self._peek(-1)
        end_pos = self._get_source_position(end_token)
        end_pos.offset += len(end_token.value)
        end_pos.column += len(end_token.value)
        
        is_suspend = 'suspend' in modifiers
        
        return ASTNode(
            node_type=NodeType.FUNCTION_DECLARATION,
            text=f"fun {function_name}()",
            range=SourceRange(start=start_pos, end=end_pos),
            children=body or [],
            metadata={
                'function_name': function_name,
                'is_suspend': is_suspend,
                'modifiers': modifiers
            }
        )
    
    def _parse_property_declaration(self, modifiers: List[str], annotations: List[ASTNode]) -> ASTNode:
        """解析属性声明"""
        start_token = self._advance()  # val/var
        start_pos = self._get_source_position(start_token)
        
        is_mutable = start_token.type == TokenType.VAR
        
        # 属性名
        property_name = ""
        if self._check(TokenType.IDENTIFIER):
            property_name = self._advance().value
        
        # 类型
        if self._match(TokenType.COLON):
            self._skip_type()
        
        # 初始值
        if self._match(TokenType.ASSIGN):
            self._skip_expression()
        
        # 委托
        if self._match(TokenType.BY):
            self._skip_expression()
        
        # getter/setter
        if self._check(TokenType.LBRACE):
            body = self._parse_class_body()  # 复用类体解析
        
        end_token = self._peek(-1)
        end_pos = self._get_source_position(end_token)
        end_pos.offset += len(end_token.value)
        end_pos.column += len(end_token.value)
        
        return ASTNode(
            node_type=NodeType.PROPERTY_DECLARATION,
            text=f"{start_token.value} {property_name}",
            range=SourceRange(start=start_pos, end=end_pos),
            children=[],
            metadata={
                'property_name': property_name,
                'is_mutable': is_mutable,
                'modifiers': modifiers
            }
        )
    
    def _parse_class_body(self) -> List[ASTNode]:
        """解析类体"""
        self._match(TokenType.LBRACE)  # consume {
        
        members = []
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            saved_pos = self.pos
            
            # 注解
            annotations = self._parse_annotations()
            
            # 修饰符
            modifiers = self._parse_modifiers()
            
            # 成员声明
            if self._check(TokenType.FUN):
                members.append(self._parse_function_declaration(modifiers, annotations))
            elif self._check(TokenType.VAL) or self._check(TokenType.VAR):
                members.append(self._parse_property_declaration(modifiers, annotations))
            elif self._check(TokenType.CLASS) or self._check(TokenType.INTERFACE):
                members.append(self._parse_class_declaration(modifiers, annotations))
            elif self._check(TokenType.OBJECT):
                members.append(self._parse_object_declaration(modifiers, annotations))
            elif self._check(TokenType.COMPANION):
                members.append(self._parse_object_declaration(modifiers, annotations))
            elif self._check(TokenType.INIT):
                # init块
                self._advance()  # init
                if self._check(TokenType.LBRACE):
                    self._parse_block()
            else:
                # 跳过未知内容
                if self.pos == saved_pos:
                    self._advance()
        
        self._match(TokenType.RBRACE)  # consume }
        return members
    
    def _parse_block(self) -> List[ASTNode]:
        """解析代码块"""
        self._match(TokenType.LBRACE)  # consume {
        
        statements = []
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            # 简化：跳过直到 }
            if self._match(TokenType.LBRACE):
                self._skip_balanced('{', '}')
            else:
                self._advance()
        
        self._match(TokenType.RBRACE)  # consume }
        return statements
    
    def _skip_balanced(self, open_char: str, close_char: str):
        """跳过配对的括号"""
        depth = 1
        open_type = TokenType.LPAREN if open_char == '(' else TokenType.LBRACE if open_char == '{' else TokenType.LBRACKET
        close_type = TokenType.RPAREN if close_char == ')' else TokenType.RBRACE if close_char == '}' else TokenType.RBRACKET
        
        while depth > 0 and not self._is_at_end():
            if self._check(open_type):
                self._advance()
                depth += 1
            elif self._check(close_type):
                self._advance()
                depth -= 1
            else:
                self._advance()
    
    def _skip_type_parameters(self):
        """跳过类型参数"""
        depth = 1
        while depth > 0 and not self._is_at_end():
            if self._match(TokenType.LT):
                depth += 1
            elif self._match(TokenType.GT):
                depth -= 1
            else:
                self._advance()
    
    def _skip_value_parameters(self):
        """跳过值参数列表"""
        depth = 1
        while depth > 0 and not self._is_at_end():
            if self._check(TokenType.LPAREN):
                self._advance()
                depth += 1
            elif self._check(TokenType.RPAREN):
                self._advance()
                depth -= 1
            elif self._check(TokenType.LBRACE):
                # 遇到代码块，参数列表结束
                break
            else:
                self._advance()
    
    def _skip_super_types(self):
        """跳过父类型声明"""
        while not self._check(TokenType.LBRACE) and not self._check(TokenType.WHERE) and not self._is_at_end():
            if self._match(TokenType.COMMA):
                continue
            self._advance()
    
    def _skip_where_clause(self):
        """跳过where子句"""
        self._advance()  # where
        while not self._check(TokenType.LBRACE) and not self._check(TokenType.ASSIGN) and not self._is_at_end():
            if self._match(TokenType.COMMA):
                continue
            self._advance()
    
    def _skip_type(self):
        """跳过类型声明"""
        while not self._is_at_end():
            if self._check(TokenType.COMMA) or self._check(TokenType.RBRACE) or \
               self._check(TokenType.LBRACE) or self._check(TokenType.ASSIGN) or \
               self._check(TokenType.LPAREN) or self._check(TokenType.RPAREN) or \
               self._check(TokenType.FUN) or self._check(TokenType.VAL) or self._check(TokenType.VAR):
                break
            if self._match(TokenType.LT):
                self._skip_type_parameters()
            else:
                self._advance()
    
    def _skip_expression(self):
        """跳过表达式"""
        depth = 0
        while not self._is_at_end():
            if self._check(TokenType.LBRACE):
                if depth == 0:
                    break
                depth -= 1
                self._advance()
            elif self._check(TokenType.RBRACE):
                if depth == 0:
                    break
                depth += 1
                self._advance()
            elif self._check(TokenType.SEMICOLON) or self._check(TokenType.COMMA):
                if depth == 0:
                    break
                self._advance()
            else:
                self._advance()


# ==================== 便捷函数 ====================

def parse_kotlin_ast(source: str) -> ASTNode:
    """
    解析Kotlin源码为AST
    
    Args:
        source: Kotlin源代码
        
    Returns:
        AST根节点
    """
    lexer = KotlinLexer(source)
    tokens = lexer.tokenize()
    parser = KotlinParser(tokens, source)
    return parser.parse()


def analyze_kotlin_file(filepath: str) -> Optional[ASTNode]:
    """
    分析Kotlin文件
    
    Args:
        filepath: 文件路径
        
    Returns:
        AST根节点或None
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        return parse_kotlin_ast(source)
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return None
