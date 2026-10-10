import 'dart:convert';
import 'dart:io';
import 'package:analyzer/dart/analysis/utilities.dart';
import 'package:analyzer/dart/ast/ast.dart';
import 'package:analyzer/dart/ast/visitor.dart';
import 'package:analyzer/dart/analysis/features.dart';

// Audit-only: parse source; never import or execute the product being inspected.
class BodyFacts extends RecursiveAstVisitor<void> {
  final List<Map<String, Object?>> calls = [];
  final List<Map<String, Object?>> guards = [];
  final List<Map<String, Object?>> returns = [];
  final List<Map<String, Object?>> writes = [];
  final List<Map<String, Object?>> catches = [];
  final List<Map<String, Object?>> awaits = [];
  @override
  void visitFunctionExpression(FunctionExpression node) {}
  @override
  void visitFunctionDeclaration(FunctionDeclaration node) {}
  @override
  void visitMethodInvocation(MethodInvocation n) {
    calls.add({'offset': n.offset, 'method': n.methodName.name,
      'target': n.target?.toSource(), 'arguments': n.argumentList.toSource()});
    super.visitMethodInvocation(n);
  }
  @override
  void visitInstanceCreationExpression(InstanceCreationExpression n) {
    calls.add({'offset': n.offset, 'constructor': n.constructorName.toSource(),
      'arguments': n.argumentList.toSource()});
    super.visitInstanceCreationExpression(n);
  }
  @override
  void visitFunctionExpressionInvocation(FunctionExpressionInvocation n) {
    calls.add({'offset': n.offset, 'function': n.function.toSource(),
      'arguments': n.argumentList.toSource()});
    super.visitFunctionExpressionInvocation(n);
  }
  @override
  void visitIfStatement(IfStatement n) {
    guards.add({'offset': n.offset, 'condition': n.expression.toSource(),
      'then': n.thenStatement.toSource(), 'else': n.elseStatement?.toSource()});
    super.visitIfStatement(n);
  }
  @override
  void visitReturnStatement(ReturnStatement n) {
    returns.add({'offset': n.offset, 'kind': 'return', 'value': n.expression?.toSource()});
    super.visitReturnStatement(n);
  }
  @override
  void visitThrowExpression(ThrowExpression n) {
    returns.add({'offset': n.offset, 'kind': 'throw', 'value': n.expression.toSource()});
    super.visitThrowExpression(n);
  }
  @override
  void visitAssignmentExpression(AssignmentExpression n) {
    writes.add({'offset': n.offset, 'left': n.leftHandSide.toSource(),
      'operator': n.operator.lexeme, 'right': n.rightHandSide.toSource()});
    super.visitAssignmentExpression(n);
  }
  @override
  void visitCatchClause(CatchClause n) {
    catches.add({'offset': n.offset, 'type': n.exceptionType?.toSource(),
      'body': n.body.toSource()});
    super.visitCatchClause(n);
  }
  @override
  void visitAwaitExpression(AwaitExpression n) {
    awaits.add({'offset': n.offset, 'expression': n.expression.toSource()});
    super.visitAwaitExpression(n);
  }
}

class FunctionFacts extends RecursiveAstVisitor<void> {
  FunctionFacts(this.path, this.content, this.location);
  final String path, content;
  final int Function(int) location;
  final List<Map<String, Object?>> functions = [];
  String? declaredName(AstNode n, String keyword) {
    var token = n.beginToken;
    while (token.offset < n.end && !token.isEof) {
      if (token.lexeme == keyword) return token.next?.lexeme;
      final next = token.next;
      if (next == null || identical(next, token)) break;
      token = next;
    }
    return null;
  }
  String? owner(AstNode n) {
    AstNode? p = n.parent;
    while (p != null) {
      if (p is ClassDeclaration) return declaredName(p, 'class');
      if (p is MixinDeclaration) return p.name.lexeme;
      if (p is ExtensionDeclaration) return p.name?.lexeme;
      if (p is EnumDeclaration) return declaredName(p, 'enum');
      p = p.parent;
    }
    return null;
  }
  void add(AstNode n, String name, FunctionBody body, String? parameters,
      String? returnType, String kind, {String? initialization}) {
    final f = BodyFacts(); body.accept(f);
    final own = owner(n);
    final qualified = own == null ? name : '$own.$name';
    final expression = body is ExpressionFunctionBody ? body.expression.toSource() : null;
    functions.add({'path': path, 'name': qualified, 'kind': kind,
      'offset': n.offset, 'end_offset': n.end, 'line': location(n.offset),
      'end_line': location(n.end > n.offset ? n.end - 1 : n.end),
      'id': '$path::$qualified@${location(n.offset)}:${n.offset}',
      'parameters': parameters, 'return_type': returnType,
      'is_async': body.isAsynchronous, 'is_generator': body.isGenerator,
      'body_kind': body.runtimeType.toString(),
      'body': content.substring(body.offset, body.end),
      'expression_result': expression, 'initialization': initialization,
      'calls': f.calls, 'guards': f.guards, 'returns': f.returns,
      'writes': f.writes, 'catches': f.catches, 'awaits': f.awaits,
      'analysis_boundary': 'NATIVE_AST_BEHAVIOR_IR_NOT_RUNTIME_ACCEPTANCE'});
  }
  @override
  void visitMethodDeclaration(MethodDeclaration n) {
    add(n, n.name.lexeme, n.body, n.parameters?.toSource(), n.returnType?.toSource(),
      n.isGetter ? 'getter' : n.isSetter ? 'setter' : 'method');
    super.visitMethodDeclaration(n);
  }
  @override
  void visitConstructorDeclaration(ConstructorDeclaration n) {
    add(n, '<constructor>' + (n.name == null ? '' : '.${n.name!.lexeme}'),
      n.body, n.parameters.toSource(), null, 'constructor',
      initialization: n.initializers.map((x) => x.toSource()).join(', '));
    super.visitConstructorDeclaration(n);
  }
  @override
  void visitFunctionDeclaration(FunctionDeclaration n) {
    add(n, n.name.lexeme, n.functionExpression.body,
      n.functionExpression.parameters?.toSource(), n.returnType?.toSource(), 'function');
    super.visitFunctionDeclaration(n);
  }
  @override
  void visitFunctionExpression(FunctionExpression n) {
    if (n.parent is! FunctionDeclaration) {
      add(n, '<closure:${n.offset}>', n.body, n.parameters?.toSource(), null, 'closure');
    }
    super.visitFunctionExpression(n);
  }
}

void main(List<String> args) {
  if (args.length != 2) throw ArgumentError('source-root output-json');
  final root = Directory(args[0]).absolute;
  final paths = root.listSync(recursive: true, followLinks: false)
      .whereType<File>().where((p) => p.path.endsWith('.dart') &&
          !p.path.contains('/.dart_tool/') && !p.path.contains('/build/'))
      .toList()..sort((a, b) => a.path.compareTo(b.path));
  final output = <Map<String, Object?>>[];
  for (final file in paths) {
    final content = file.readAsStringSync();
    final path = file.path.substring(root.path.length + 1);
    final parsed = parseString(content: content, path: path,
      featureSet: FeatureSet.latestLanguageVersion(), throwIfDiagnostics: false);
    final visitor = FunctionFacts(path, content, (offset) => parsed.lineInfo.getLocation(offset).lineNumber);
    parsed.unit.accept(visitor);
    output.add({'path': path, 'parse_errors': parsed.errors.map((e) =>
      {'offset': e.offset, 'length': e.length, 'message': e.message}).toList(),
      'functions': visitor.functions});
  }
  final summary = {'source_root': 'FROZEN_SOURCE',
    'baseline': '01588e9fd9568e3fcaf1e6c3d957bc498436fa48',
    'dart_runtime': Platform.version, 'observed_at': DateTime.now().toUtc().toIso8601String(),
    'files': output, 'runtime_started': false, 'product_imports_executed': false};
  File(args[1]).writeAsStringSync(jsonEncode(summary));
  print(jsonEncode({'files': output.length,
    'function_units': output.fold<int>(0, (n, f) => n + (f['functions'] as List).length),
    'diagnostics': output.fold<int>(0, (n, f) => n + (f['parse_errors'] as List).length),
    'product_runtime_started': false}));
}
