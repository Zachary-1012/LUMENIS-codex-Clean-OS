// Audit helper only. Parse source; never import, build, or run the product.
import 'dart:convert';
import 'dart:io';
import 'package:analyzer/dart/analysis/features.dart';
import 'package:analyzer/dart/analysis/utilities.dart';
import 'package:analyzer/dart/ast/ast.dart';
import 'package:analyzer/dart/ast/visitor.dart';

bool boundary(AstNode n) => n is MethodDeclaration || n is FunctionDeclaration || n is ConstructorDeclaration || n is FunctionExpression;
Map<String,Object?> astMap(AstNode node) {
  final value=<String,Object?>{'kind':node.runtimeType.toString().replaceAll('Impl',''),'offset':node.offset,'length':node.length};
  value['children']=node.childEntities.whereType<AstNode>().map(astMap).toList();
  List<int>? ref(AstNode? n)=>n==null?null:[n.offset,n.length];
  if(node is IfStatement) value.addAll({'test':ref(node.expression),'then':ref(node.thenStatement),'else':ref(node.elseStatement)});
  if(node is WhileStatement) value.addAll({'test':ref(node.condition),'body':ref(node.body)});
  if(node is DoStatement) value.addAll({'test':ref(node.condition),'body':ref(node.body)});
  if(node is ForStatement) value.addAll({'loop':ref(node.forLoopParts),'body':ref(node.body)});
  if(node is TryStatement) value.addAll({'body':ref(node.body),'finally':ref(node.finallyBlock)});
  if(node is VariableDeclaration) value.addAll({'name':node.name.lexeme,'initializer':ref(node.initializer)});
  if(node is AssignmentExpression) value.addAll({'target':ref(node.leftHandSide),'value':ref(node.rightHandSide),'operator':node.operator.lexeme});
  if(node is ReturnStatement) value['expression']=ref(node.expression);
  if(node is ThrowExpression) value['expression']=ref(node.expression);
  return value;
}
class BodyFacts extends GeneralizingAstVisitor<void> {
  BodyFacts(this.root);
  final AstNode root;
  final calls = <Map<String, Object?>>[];
  final returns = <Map<String, Object?>>[];
  final awaits = <int>[];
  final branches = <Map<String, Object?>>[];
  final assignments = <Map<String, Object?>>[];
  final exceptions = <Map<String, Object?>>[];
  @override
  void visitNode(AstNode node) {
    if (node != root && boundary(node) && !(root is FunctionDeclaration && node == (root as FunctionDeclaration).functionExpression)) return;
    if (node is MethodInvocation) calls.add({'offset':node.offset,'target':node.target?.toSource(),'name':node.methodName.name,'arguments':node.argumentList.arguments.map((v)=>v.toSource()).toList(),'argument_names':node.argumentList.arguments.whereType<NamedExpression>().map((v)=>v.name.label.name).toList()});
    if (node is InstanceCreationExpression) calls.add({'offset':node.offset,'constructor':node.constructorName.toSource(),'arguments':node.argumentList.arguments.map((v)=>v.toSource()).toList()});
    if (node is FunctionExpressionInvocation) calls.add({'offset':node.offset,'function':node.function.toSource(),'arguments':node.argumentList.arguments.map((v)=>v.toSource()).toList()});
    if (node is ReturnStatement) returns.add({'offset':node.offset,'expression':node.expression?.toSource()});
    if (node is ExpressionFunctionBody) returns.add({'offset':node.offset,'expression':node.expression.toSource()});
    if (node is AwaitExpression) awaits.add(node.offset);
    if (node is IfStatement) branches.add({'offset':node.offset,'condition':node.expression.toSource()});
    if (node is ConditionalExpression) branches.add({'offset':node.offset,'condition':node.condition.toSource()});
    if (node is AssignmentExpression) assignments.add({'offset':node.offset,'target':node.leftHandSide.toSource(),'operator':node.operator.lexeme,'value':node.rightHandSide.toSource()});
    if (node is CatchClause) exceptions.add({'offset':node.offset,'type':node.exceptionType?.toSource(),'body':node.body.toSource()});
    if (node is ThrowExpression) exceptions.add({'offset':node.offset,'throw':node.expression.toSource()});
    super.visitNode(node);
  }
}
class Functions extends GeneralizingAstVisitor<void> {
  Functions(this.path, this.text, this.lineForOffset);
  final String path, text;
  final int Function(int) lineForOffset;
  final rows = <Map<String, Object?>>[];
  @override
  void visitNode(AstNode node) {
    String? name,kind,parameters;
    if (node is MethodDeclaration) {name=node.name.lexeme;kind=node.isGetter?'getter':node.isSetter?'setter':'method';parameters=node.parameters?.toSource();}
    if (node is FunctionDeclaration) {name=node.name.lexeme;kind='function';parameters=node.functionExpression.parameters?.toSource();}
    if (node is ConstructorDeclaration) {name=node.returnType.toSource()+(node.name==null?'':'.${node.name!.lexeme}');kind='constructor';parameters=node.parameters.toSource();}
    if (node is FunctionExpression && node.parent is! FunctionDeclaration) {name='<closure@${node.offset}>';kind='closure';parameters=node.parameters?.toSource();}
    if (name!=null) {
      final facts=BodyFacts(node);node.accept(facts);
      final owners=<String>[];AstNode? parent=node.parent;
      while(parent!=null) {
        if(parent is ClassDeclaration) owners.add(parent.name.lexeme);
        if(parent is MethodDeclaration) owners.add(parent.name.lexeme);
        if(parent is FunctionDeclaration) owners.add(parent.name.lexeme);
        parent=parent.parent;
      }
      rows.add({'path':path,'name':name,'kind':kind,'qualname':'${owners.reversed.join('.')}${owners.isEmpty?'':'.'}$name','offset':node.offset,'length':node.length,'line':lineForOffset(node.offset),'end_line':lineForOffset(node.end),'parameters':parameters,'calls':facts.calls,'returns':facts.returns,'await_offsets':facts.awaits,'branches':facts.branches,'assignments':facts.assignments,'exceptions':facts.exceptions,'semantic_review':'FACTS_EXTRACTED_REVIEW_REQUIRED'});
    }
    super.visitNode(node);
  }
}
void main(List<String> args) {
  final root=Directory(args[0]).absolute;final out=Directory(args[1])..createSync(recursive:true);
  final files=root.listSync(recursive:true,followLinks:false).whereType<File>().where((f)=>f.path.endsWith('.dart')).toList()..sort((a,b)=>a.path.compareTo(b.path));
  final records=<Map<String,Object?>>[];final inventory=<Map<String,Object?>>[];
  final treeFile=File('${out.path}/dart_ast.jsonl').openSync(mode:FileMode.write);
  for(final file in files) {
    final path=file.path.substring(root.path.length+1).replaceAll('\\','/');final text=file.readAsStringSync();
    final parsed=parseString(content:text,path:file.path,throwIfDiagnostics:false,featureSet:FeatureSet.latestLanguageVersion());
    final visitor=Functions(path,text,(offset)=>parsed.lineInfo.getLocation(offset).lineNumber);parsed.unit.accept(visitor);
    records.addAll(visitor.rows);
    inventory.add({'path':path,'functions':visitor.rows.length,'diagnostics':parsed.errors.map((e)=>{'offset':e.offset,'length':e.length,'code':e.errorCode.name,'message':e.message}).toList()});
    treeFile.writeStringSync(jsonEncode({'path':path,'tree':astMap(parsed.unit)})+'\n');
  }
  treeFile.closeSync();
  File('${out.path}/dart_functions.jsonl').writeAsStringSync(records.map(jsonEncode).join('\n')+'\n');
  File('${out.path}/dart_files.json').writeAsStringSync(jsonEncode(inventory));
  File('${out.path}/dart_summary.json').writeAsStringSync(jsonEncode({'files':files.length,'functions_and_closures':records.length,'diagnostic_files':inventory.where((f)=>(f['diagnostics'] as List).isNotEmpty).length,'sdk':Platform.version,'source_execution':false}));
  stdout.writeln(jsonEncode({'files':files.length,'functions_and_closures':records.length,'diagnostic_files':inventory.where((f)=>(f['diagnostics'] as List).isNotEmpty).length}));
}
