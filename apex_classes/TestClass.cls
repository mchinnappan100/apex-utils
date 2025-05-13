public class TestClass {
    public void query() {
        List accounts = [SELECT Id, Name FROM Account WHERE Industry = 'Tech'];
    }
}